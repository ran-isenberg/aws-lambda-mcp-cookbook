# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
## originally from https://github.com/awslabs/mcp/tree/main/src/mcp-lambda-handler but heavily refactored
import functools
import http
import inspect
from contextvars import ContextVar
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    get_args,
    get_origin,
    get_type_hints,
)

from aws_lambda_powertools.utilities.parser import parse

from service.handlers.utils.observability import logger
from service.mcp_lambda_handler.constants import (
    CONTENT_TYPE_JSON,
    ERROR_INTERNAL,
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE,
    ERROR_SERVER,
    MCP_PROTOCOL_VERSION,
    MCP_VERSION,
)
from service.mcp_lambda_handler.models import (
    MCPAPIGatewayProxyEventBase,
    MCPDeleteAPIGatewayProxyEvent,
    MCPMethod,
    MCPPostAPIGatewayProxyEvent,
)
from service.mcp_lambda_handler.session import SessionStore
from service.mcp_lambda_handler.session_data import SessionData
from service.mcp_lambda_handler.types import (
    Capabilities,
    ErrorContent,
    InitializeResult,
    JSONRPCError,
    JSONRPCResponse,
    ServerInfo,
    TextContent,
)

# Context variable to store current session ID
current_session_id: ContextVar[Optional[str]] = ContextVar('current_session_id', default=None)


class MCPLambdaHandler:
    """A class to handle MCP (Model Context Protocol) HTTP events in AWS Lambda."""

    def __init__(self, name: str, version: str, session_store: SessionStore):
        """Initialize the MCP handler.

        Args:
            name: Handler name
            version: Handler version
            session_store: A SessionStore instance

        """
        self.name = name
        self.version = version
        self.tools: Dict[str, Dict] = {}
        self.tool_implementations: Dict[str, Callable] = {}
        self.session_store = session_store

    def get_session(self) -> Optional[SessionData]:
        """Get the current session data wrapper.

        Returns:
            SessionData object or None if no session exists

        """
        session_id = current_session_id.get()
        if not session_id:
            return None
        data = self.session_store.get_session(session_id)
        return SessionData(data) if data is not None else None

    def set_session(self, data: Dict[str, Any]) -> bool:
        """Set the entire session data.

        Args:
            data: New session data

        Returns:
            True if successful, False if no session exists

        """
        session_id = current_session_id.get()
        if not session_id:
            return False
        return self.session_store.update_session(session_id, data)

    def update_session(self, updater_func: Callable[[SessionData], None]) -> bool:
        """Update session data using a function.

        Args:
            updater_func: Function that takes SessionData and updates it in place

        Returns:
            True if successful, False if no session exists

        """
        session = self.get_session()
        if not session:
            return False

        # Update the session data
        updater_func(session)

        # Save back to storage
        return self.set_session(session.raw())

    def tool(self):  # noqa: C901
        """Create a decorator for a function as an MCP tool.

        Uses function name, docstring, and type hints to generate the MCP tool schema.
        """

        def decorator(func: Callable):  # noqa: C901
            # Get function name and convert to camelCase for tool name
            func_name = func.__name__
            tool_name = ''.join([func_name.split('_')[0]] + [word.capitalize() for word in func_name.split('_')[1:]])

            # Get docstring and parse into description
            doc = inspect.getdoc(func) or ''
            description = doc.split('\n\n')[0]  # First paragraph is description

            # Get type hints
            hints = get_type_hints(func)
            # return_type = hints.pop('return', Any)
            hints.pop('return', Any)

            # Build input schema from type hints and docstring
            properties = {}
            required = []

            # Parse docstring for argument descriptions
            arg_descriptions = {}
            if doc:
                lines = doc.split('\n')
                in_args = False
                for line in lines:
                    if line.strip().startswith('Args:'):
                        in_args = True
                        continue
                    if in_args:
                        if not line.strip() or line.strip().startswith('Returns:'):
                            break
                        if ':' in line:
                            arg_name, arg_desc = line.split(':', 1)
                            arg_descriptions[arg_name.strip()] = arg_desc.strip()

            def get_type_schema(type_hint: Any) -> Dict[str, Any]:  # noqa: C901
                # Handle basic types
                if type_hint is int:
                    return {'type': 'integer'}
                elif type_hint is float:
                    return {'type': 'number'}
                elif type_hint is bool:
                    return {'type': 'boolean'}
                elif type_hint is str:
                    return {'type': 'string'}

                # Handle Enums
                if isinstance(type_hint, type) and issubclass(type_hint, Enum):
                    return {'type': 'string', 'enum': [e.value for e in type_hint]}

                # Get origin type (e.g., Dict from Dict[str, int])
                origin = get_origin(type_hint)
                if origin is None:
                    return {'type': 'string'}  # Default for unknown types

                # Handle Dict types
                if origin is dict or origin is Dict:
                    args = get_args(type_hint)
                    if not args:
                        return {'type': 'object', 'additionalProperties': True}

                    # Get value type schema (args[1] is value type)
                    value_schema = get_type_schema(args[1])
                    return {'type': 'object', 'additionalProperties': value_schema}

                # Handle List types
                if origin is list or origin is List:
                    args = get_args(type_hint)
                    if not args:
                        return {'type': 'array', 'items': {}}

                    item_schema = get_type_schema(args[0])
                    return {'type': 'array', 'items': item_schema}

                # Default for unknown complex types
                return {'type': 'string'}

            # Build properties from type hints
            for param_name, param_type in hints.items():
                param_schema = get_type_schema(param_type)

                if param_name in arg_descriptions:
                    param_schema['description'] = arg_descriptions[param_name]

                properties[param_name] = param_schema
                required.append(param_name)

            # Create tool schema
            tool_schema = {
                'name': tool_name,
                'description': description,
                'inputSchema': {'type': 'object', 'properties': properties, 'required': required},
            }

            # Register the tool
            self.tools[tool_name] = tool_schema
            self.tool_implementations[tool_name] = func

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def _create_error_response(
        self,
        code: int,
        message: str,
        request_id: Optional[str] = None,
        error_content: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        status_code: Optional[int] = None,
        data: Optional[Dict] = None,
    ) -> Dict:
        """Create a standardized error response."""
        error = JSONRPCError(code=code, message=message, data=data)
        response = JSONRPCResponse(jsonrpc='2.0', id=request_id, error=error, errorContent=error_content)

        headers = {'Content-Type': CONTENT_TYPE_JSON, 'MCP-Version': MCP_VERSION}
        if session_id:
            headers['MCP-Session-Id'] = session_id

        return {
            'statusCode': status_code or self._error_code_to_http_status(code),
            'body': response.model_dump_json(),
            'headers': headers,
        }

    def _error_code_to_http_status(self, error_code: int) -> int:
        """Map JSON-RPC error codes to HTTP status codes."""
        error_map = {
            ERROR_PARSE: http.HTTPStatus.BAD_REQUEST.value,  # Parse error
            ERROR_INVALID_REQUEST: http.HTTPStatus.BAD_REQUEST.value,  # Invalid Request
            ERROR_METHOD_NOT_FOUND: http.HTTPStatus.NOT_FOUND.value,  # Method not found
            ERROR_INVALID_PARAMS: http.HTTPStatus.BAD_REQUEST.value,  # Invalid params
            ERROR_INTERNAL: http.HTTPStatus.INTERNAL_SERVER_ERROR.value,  # Internal error
        }
        return error_map.get(error_code, http.HTTPStatus.INTERNAL_SERVER_ERROR.value)

    def _create_success_response(self, result: Any, request_id: str | None, session_id: Optional[str] = None) -> Dict:
        """Create a standardized success response."""
        response = JSONRPCResponse(jsonrpc='2.0', id=request_id, result=result)

        headers = {'Content-Type': CONTENT_TYPE_JSON, 'MCP-Version': MCP_VERSION}
        if session_id:
            headers['MCP-Session-Id'] = session_id

        return {'statusCode': http.HTTPStatus.OK.value, 'body': response.model_dump_json(), 'headers': headers}

    def handle_request(self, event: Dict, context: Any) -> Dict:
        """Handle an incoming Lambda request."""
        request_id = None
        session_id = None
        current_session_id.set(None)

        # Get the HTTP method to determine which model to use
        http_method = event.get('httpMethod')
        logger.debug('HTTP method', extra={'http_method': http_method})

        try:
            # Use the appropriate model based on HTTP method
            if http_method == 'DELETE':
                parsed_event = parse(event=event, model=MCPDeleteAPIGatewayProxyEvent)
                request_id = None  # DELETE requests don't have a request_id
            elif http_method == 'POST':
                parsed_event = parse(event=event, model=MCPPostAPIGatewayProxyEvent)
                request_id = parsed_event.body.id if hasattr(parsed_event, 'body') else None
            else:
                return self._create_error_response(ERROR_INVALID_REQUEST, f'Unsupported HTTP method: {http_method}')
        except Exception:
            logger.exception('Error parsing event', exc_info=True)
            return self._create_error_response(code=ERROR_INVALID_REQUEST, message='Parse error')

        # Set current session ID in context
        session_id = parsed_event.mcp_session_id
        if session_id:
            current_session_id.set(session_id)
            logger.debug('session_id found', extra={'session_id': session_id})

        # Switch-like structure for HTTP method handling
        try:
            match parsed_event.httpMethod:
                case 'DELETE':
                    return self._handle_http_delete(parsed_event, request_id, session_id)
                case 'POST':
                    return self._handle_http_post(parsed_event, request_id, session_id)
                case _:  # Default case for unsupported methods
                    return self._create_error_response(ERROR_INVALID_REQUEST, f'Unsupported HTTP method: {parsed_event.httpMethod}')
        except Exception:
            logger.exception('Error handling request', exc_info=True)
            return self._create_error_response(
                code=ERROR_INTERNAL,
                message='Internal server error',
                request_id=request_id,
                session_id=session_id,
            )

    def _handle_initialize(self, parsed_event: MCPAPIGatewayProxyEventBase, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle an 'initialize' MCP method request."""
        logger.info('Handling initialize request')
        # Create new session
        session_id = self.session_store.create_session()
        current_session_id.set(session_id)
        logger.debug('session_id created', extra={'session_id': session_id})
        result = InitializeResult(
            protocolVersion=MCP_PROTOCOL_VERSION,
            serverInfo=ServerInfo(name=self.name, version=self.version),
            capabilities=Capabilities(tools={'list': True, 'call': True}),
        )
        return self._create_success_response(result.model_dump(), request_id, session_id)

    def _handle_tools_list(self, parsed_event: MCPAPIGatewayProxyEventBase, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle a 'tools/list' MCP method request."""
        logger.info('Handling tools/list request')
        return self._create_success_response({'tools': list(self.tools.values())}, request_id, session_id)

    def _handle_tools_call(self, parsed_event: MCPAPIGatewayProxyEventBase, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle a 'tools/call' MCP method request."""
        if not parsed_event.body.params:
            return self._create_error_response(ERROR_INVALID_PARAMS, 'Missing parameters for tools/call', request_id, session_id=session_id)

        if not self._validate_session(request_id, session_id):
            return self._create_error_response(ERROR_SERVER, 'Invalid or expired session', request_id, status_code=http.HTTPStatus.NOT_FOUND.value)

        tool_name = parsed_event.body.params.get('name')
        tool_args = parsed_event.body.params.get('arguments', {})

        if tool_name not in self.tools:
            return self._create_error_response(ERROR_METHOD_NOT_FOUND, f"Tool '{tool_name}' not found", request_id, session_id=session_id)

        try:
            # Convert enum string values to enum objects
            converted_args = {}
            tool_func = self.tool_implementations[tool_name]
            hints = get_type_hints(tool_func)

            for arg_name, arg_value in tool_args.items():
                arg_type = hints.get(arg_name)
                if isinstance(arg_type, type) and issubclass(arg_type, Enum):
                    converted_args[arg_name] = arg_type(arg_value)
                else:
                    converted_args[arg_name] = arg_value

            result = tool_func(**converted_args)
            content = [TextContent(text=str(result)).model_dump()]
            return self._create_success_response({'content': content}, request_id, session_id)
        except Exception as e:
            logger.exception(f'Error executing tool {tool_name}: {e}')
            error_content = [ErrorContent(text=str(e)).model_dump()]
            return self._create_error_response(
                ERROR_INTERNAL,
                f'Error executing tool: {str(e)}',
                request_id,
                error_content,
                session_id,
            )

    def _handle_ping(self, parsed_event: MCPAPIGatewayProxyEventBase, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle a 'ping' MCP method request."""
        logger.info('Handling ping request')
        return self._create_success_response({}, request_id, session_id)

    def _handle_http_delete(self, parsed_event: MCPDeleteAPIGatewayProxyEvent, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle HTTP DELETE requests, used for session deletion."""
        if session_id:
            logger.debug('deleting session', extra={'session_id': session_id})
            self.session_store.delete_session(session_id)
            return {'statusCode': http.HTTPStatus.NO_CONTENT.value}
        else:
            logger.debug('session not found, cant delete session', extra={'session_id': session_id})
            return {'statusCode': http.HTTPStatus.NOT_FOUND.value}

    def _handle_http_post(self, parsed_event: MCPPostAPIGatewayProxyEvent, request_id: Optional[str], session_id: Optional[str]) -> Dict:
        """Handle HTTP POST requests containing JSON-RPC calls."""
        # Map of method handlers
        method_handlers = {
            MCPMethod.INITIALIZE: self._handle_initialize,
            MCPMethod.TOOLS_LIST: self._handle_tools_list,
            MCPMethod.TOOLS_CALL: self._handle_tools_call,
            MCPMethod.PING: self._handle_ping,
        }

        if parsed_event.headers.content_type != CONTENT_TYPE_JSON:
            return self._create_error_response(ERROR_PARSE, 'Unsupported Media Type')

        # Check if this is a notification (no id field)
        if parsed_event.body.method == MCPMethod.NOTIFICATION:
            logger.debug('Request is a notification')
            return {
                'statusCode': http.HTTPStatus.ACCEPTED.value,  # MCP spec requires 202 Accepted for notifications
                'body': '',
                'headers': {'Content-Type': CONTENT_TYPE_JSON, 'MCP-Version': MCP_VERSION},
            }
        if not session_id:
            logger.debug('No session ID provided', extra={'session_id': session_id})
            # If no session ID is provided, we assume this is an initialize request
            if parsed_event.body.method != MCPMethod.INITIALIZE:
                return self._create_error_response(
                    ERROR_INVALID_REQUEST, 'Session required', request_id, status_code=http.HTTPStatus.BAD_REQUEST.value
                )

        # Use method handlers dictionary to dispatch to the appropriate handler
        if parsed_event.body.method in method_handlers:
            return method_handlers[parsed_event.body.method](parsed_event, request_id, session_id)

        # Handle unknown methods
        return self._create_error_response(ERROR_METHOD_NOT_FOUND, f'Method not found: {parsed_event.body.method}', request_id, session_id=session_id)

    def _validate_session(self, request_id: str, session_id: str) -> bool:
        """Validate the session ID."""
        logger.debug('Validating session', extra={'session_id': session_id})
        session_data = self.session_store.get_session(session_id)
        if session_data is None:
            return False
        return True
