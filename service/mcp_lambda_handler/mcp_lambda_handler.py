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
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
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
    MCPDeleteAPIGatewayProxyEvent,
    MCPMethod,
    MCPPostAPIGatewayProxyEvent,
)
from service.mcp_lambda_handler.session import SessionStore
from service.mcp_lambda_handler.session_data import SessionData
from service.mcp_lambda_handler.types import (
    Capabilities,
    InitializeResult,
    JSONRPCError,
    JSONRPCResponse,
    ServerInfo,
    TextContent,
)


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
        self.session_id: Optional[str] = None
        self.request_id: Optional[str] = None

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            Session ID string or None if no session exists

        """
        return self.session_id

    def get_session(self) -> Optional[SessionData]:
        """Get the current session data wrapper.

        Returns:
            SessionData object or None if no session exists

        """
        if not self.session_id:
            return None
        data = self.session_store.get_session(self.session_id)
        return SessionData(data) if data is not None else None

    def set_session(self, data: Dict[str, Any]) -> bool:
        """Set the entire session data.

        Args:
            data: New session data

        Returns:
            True if successful, False if no session exists

        """
        if not self.session_id:
            return False
        return self.session_store.update_session(self.session_id, data)

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
        self.request_id = None
        self.session_id = None

        # Get the HTTP method to determine which model to use
        http_method = event.get('httpMethod')
        logger.info('HTTP method', extra={'http_method': http_method})

        try:
            # Use the appropriate model based on HTTP method
            if http_method == 'DELETE':
                parsed_event = parse(event=event, model=MCPDeleteAPIGatewayProxyEvent)
            elif http_method == 'POST':
                parsed_event = parse(event=event, model=MCPPostAPIGatewayProxyEvent)
                self.request_id = parsed_event.body.id if hasattr(parsed_event, 'body') else None
            else:
                return self._create_error_response(ERROR_INVALID_REQUEST, f'Unsupported HTTP method: {http_method}')
        except Exception:
            logger.exception('Error parsing event', exc_info=True)
            return self._create_error_response(code=ERROR_INVALID_REQUEST, message='Parse error')

        # Set current session ID in context
        self.session_id = parsed_event.mcp_session_id
        if self.session_id:
            logger.debug('session_id found', extra={'session_id': self.session_id})

        # Switch-like structure for HTTP method handling
        try:
            match parsed_event.httpMethod:
                case 'DELETE':
                    return self._handle_http_delete(parsed_event)
                case 'POST':
                    return self._handle_http_post(parsed_event)
                case _:  # Default case for unsupported methods
                    return self._create_error_response(ERROR_INVALID_REQUEST, f'Unsupported HTTP method: {parsed_event.httpMethod}')
        except Exception:
            logger.exception('Error handling request', exc_info=True)
            return self._create_error_response(
                code=ERROR_INTERNAL,
                message='Internal server error',
                request_id=self.request_id,
                session_id=self.session_id,
            )

    def _handle_initialize(self, parsed_event: MCPPostAPIGatewayProxyEvent) -> Dict:
        """Handle an 'initialize' MCP method request."""
        logger.info('Handling initialize request')
        # Create new session
        self.session_id = self.session_store.create_session()
        logger.debug('session_id created', extra={'session_id': self.session_id})
        result = InitializeResult(
            protocolVersion=MCP_PROTOCOL_VERSION,
            serverInfo=ServerInfo(name=self.name, version=self.version),
            capabilities=Capabilities(tools={'list': True, 'call': True}),
        )
        return self._create_success_response(result.model_dump(), self.request_id, self.session_id)

    def _handle_tools_list(self, parsed_event: MCPPostAPIGatewayProxyEvent) -> Dict:
        """Handle a 'tools/list' MCP method request."""
        logger.info('Handling tools/list request')
        return self._create_success_response({'tools': list(self.tools.values())}, self.request_id, self.session_id)

    def _handle_tools_call(self, parsed_event: MCPPostAPIGatewayProxyEvent) -> Dict:
        """Handle a 'tools/call' MCP method request."""
        logger.info('Handling tools/call request')
        if not parsed_event.body.params:
            return self._create_error_response(
                code=ERROR_INVALID_PARAMS, message='Missing parameters for tools/call', request_id=self.request_id, session_id=self.session_id
            )

        if not self._validate_session():
            return self._create_error_response(
                code=ERROR_SERVER, message='Invalid or expired session', request_id=self.request_id, status_code=http.HTTPStatus.NOT_FOUND.value
            )

        tool_name = parsed_event.body.params.get('name')
        tool_args = parsed_event.body.params.get('arguments', {})

        if tool_name not in self.tools:
            return self._create_error_response(
                code=ERROR_METHOD_NOT_FOUND, message=f"Tool '{tool_name}' not found", request_id=self.request_id, session_id=self.session_id
            )
        logger.info('tool_name found', extra={'tool_name': tool_name})

        try:
            converted_args, error_response = self._validate_tool_args(tool_name, tool_args, self.tool_implementations[tool_name])
            if error_response:
                return error_response

            result = self.tool_implementations[tool_name](**converted_args)
            content = [TextContent(text=str(result)).model_dump()]
            return self._create_success_response(result={'content': content}, request_id=self.request_id, session_id=self.session_id)
        except Exception as e:
            logger.exception(f'Error executing tool {tool_name}: {e}')
            return self._create_error_response(
                code=ERROR_INTERNAL,
                message='Error executing tool',
                request_id=self.request_id,
                session_id=self.session_id,
            )

    def _handle_ping(self, parsed_event: MCPPostAPIGatewayProxyEvent) -> Dict:
        """Handle a 'ping' MCP method request."""
        logger.info('Handling ping request')
        return self._create_success_response({}, self.request_id, self.session_id)

    def _handle_http_delete(self, parsed_event: MCPDeleteAPIGatewayProxyEvent) -> Dict:
        """Handle HTTP DELETE requests, used for session deletion."""
        if self.session_id:
            logger.debug('deleting session', extra={'session_id': self.session_id})
            self.session_store.delete_session(self.session_id)
            return {'statusCode': http.HTTPStatus.NO_CONTENT.value}
        else:
            logger.debug('session not found, cant delete session', extra={'session_id': self.session_id})
            return {'statusCode': http.HTTPStatus.NOT_FOUND.value}

    def _handle_http_post(self, parsed_event: MCPPostAPIGatewayProxyEvent) -> Dict:
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
        if not self.session_id:
            logger.debug('No session ID provided')
            # If no session ID is provided, we assume this is an initialize request
            if parsed_event.body.method != MCPMethod.INITIALIZE:
                return self._create_error_response(
                    ERROR_INVALID_REQUEST, 'Session required', self.request_id, status_code=http.HTTPStatus.BAD_REQUEST.value
                )

        # Use method handlers dictionary to dispatch to the appropriate handler
        if parsed_event.body.method in method_handlers:
            return method_handlers[parsed_event.body.method](parsed_event)

        # Handle unknown methods
        return self._create_error_response(
            code=ERROR_METHOD_NOT_FOUND,
            message=f'Method not found: {parsed_event.body.method}',
            request_id=self.request_id,
            session_id=self.session_id,
        )

    def _validate_session(self) -> bool:
        """Validate the session ID."""
        logger.debug('Validating session', extra={'session_id': self.session_id})
        session_data = self.session_store.get_session(self.session_id)
        if session_data is None:
            return False
        return True

    def _validate_tool_args(self, tool_name: str, tool_args: Dict, tool_func: Callable) -> tuple[Dict, Optional[Dict]]:
        """Validate tool arguments against the function signature and type hints.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments provided for the tool
            tool_func: The function implementation of the tool

        Returns:
            Tuple of (converted_args, error_response)
            If validation passes, error_response will be None
            If validation fails, error_response will contain the error response to return
        """
        hints = get_type_hints(tool_func)
        signature = inspect.signature(tool_func)

        # Check for missing required parameters and unexpected parameters
        error_response = self._check_parameter_presence(tool_name, tool_args, signature)
        if error_response:
            return {}, error_response

        # Convert and validate the arguments
        return self._convert_and_validate_args(tool_name, tool_args, hints)

    def _check_parameter_presence(self, tool_name: str, tool_args: Dict, signature: inspect.Signature) -> Optional[Dict]:
        """Check if all required parameters are present and handle unexpected parameters."""
        expected_params = set(signature.parameters.keys())
        provided_params = set(tool_args.keys())

        # Check for missing required parameters
        missing_required = [
            param
            for param, param_obj in signature.parameters.items()
            if param_obj.default == inspect.Parameter.empty and param not in provided_params
        ]

        if missing_required:
            logger.error(f'Missing required parameters for tool {tool_name}: {missing_required}')
            return self._create_error_response(
                code=ERROR_INVALID_PARAMS,
                message=f'Missing required parameters: {", ".join(missing_required)}',
                request_id=self.request_id,
                session_id=self.session_id,
            )

        # Check for unexpected parameters
        unexpected_params = provided_params - expected_params
        if unexpected_params:
            logger.warning(f'Unexpected parameters for tool {tool_name}: {unexpected_params}')
            # We'll log a warning but continue, removing the unexpected parameters
            for param in unexpected_params:
                tool_args.pop(param)

        return None

    def _convert_and_validate_args(self, tool_name: str, tool_args: Dict, hints: Dict[str, Any]) -> tuple[Dict, Optional[Dict]]:
        """Convert and validate arguments based on type hints."""
        converted_args = {}

        for arg_name, arg_value in tool_args.items():
            if arg_name not in hints:
                # No type hint - use the value as-is
                converted_args[arg_name] = arg_value
                continue

            arg_type = hints[arg_name]

            # Skip conversion if value is None
            if arg_value is None:
                converted_args[arg_name] = None
                continue

            try:
                # Handle different types through helper methods
                conversion_result = self._convert_arg_value(arg_name, arg_value, arg_type)
                if isinstance(conversion_result, tuple):
                    # If a tuple is returned, it's an error
                    error_msg, expected_type = conversion_result
                    return {}, self._create_error_response(
                        code=ERROR_INVALID_PARAMS,
                        message=f"Invalid value for parameter '{arg_name}': {error_msg}",
                        request_id=self.request_id,
                        session_id=self.session_id,
                        data={'expected': expected_type, 'received': type(arg_value).__name__},
                    )

                converted_args[arg_name] = conversion_result

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Type conversion error for parameter '{arg_name}': {error_msg}")

                # Get a friendly type name for the error message
                expected_type_name = self._get_friendly_type_name(arg_type)

                return {}, self._create_error_response(
                    code=ERROR_INVALID_PARAMS,
                    message=f"Invalid value for parameter '{arg_name}': {error_msg}",
                    request_id=self.request_id,
                    session_id=self.session_id,
                    data={'expected': expected_type_name, 'received': type(arg_value).__name__},
                )

        return converted_args, None

    def _convert_arg_value(self, arg_name: str, arg_value: Any, arg_type: Any) -> Any:
        """Convert an argument value to the expected type."""
        # Handle enum types
        if isinstance(arg_type, type) and issubclass(arg_type, Enum):
            return self._convert_enum_value(arg_value, arg_type)

        # Handle primitive types
        if arg_type in (str, int, float, bool) and not isinstance(arg_value, arg_type):
            return self._convert_primitive_value(arg_value, arg_type)

        # Handle Optional types (Union[Type, None])
        if get_origin(arg_type) is Union:
            return self._convert_union_value(arg_value, arg_type)

        # Handle List types
        if get_origin(arg_type) in (list, List):
            return self._convert_list_value(arg_value, arg_type)

        # Handle Dict types
        if get_origin(arg_type) in (dict, Dict):
            if not isinstance(arg_value, dict):
                return (f'Expected dict, got {type(arg_value).__name__}', 'dictionary')
            return arg_value

        # Default case - use the value as-is
        return arg_value

    def _convert_enum_value(self, arg_value: Any, enum_type: type) -> Any:
        """Convert a value to an enum type."""
        try:
            return enum_type(arg_value)
        except ValueError:
            # Check if the enum value matches a case-insensitive name
            enum_dict = {str(e.name).lower(): e for e in enum_type}
            if isinstance(arg_value, str) and arg_value.lower() in enum_dict:
                return enum_dict[arg_value.lower()]

            # If conversion fails, return an error tuple
            return (
                f'Invalid enum value: {arg_value}. Expected one of: {[e.value for e in enum_type]}',
                f'enum [{", ".join(str(e.value) for e in enum_type)}]',
            )

    def _convert_primitive_value(self, arg_value: Any, primitive_type: type) -> Any:
        """Convert a value to a primitive type."""
        # Special handling for booleans - accept string representations
        if primitive_type is bool and isinstance(arg_value, str):
            lower_val = arg_value.lower()
            if lower_val in ('true', 'yes', '1', 'on'):
                return True
            elif lower_val in ('false', 'no', '0', 'off'):
                return False
            else:
                return (f"Cannot convert '{arg_value}' to boolean", 'boolean')

        # For other primitives, try direct conversion
        try:
            return primitive_type(arg_value)
        except (ValueError, TypeError) as e:
            return (str(e), primitive_type.__name__)

    def _convert_union_value(self, arg_value: Any, union_type: Any) -> Any:
        """Convert a value to a union type."""
        type_args = get_args(union_type)

        # Check if this is Optional[X]
        if type(None) in type_args and len(type_args) == 2:
            # Get the non-None type
            actual_type = next(t for t in type_args if t is not type(None))

            # Handle primitive types in Optional
            if actual_type in (str, int, float, bool):
                return self._convert_primitive_value(arg_value, actual_type)

            # Handle Optional[Enum]
            if isinstance(actual_type, type) and issubclass(actual_type, Enum):
                return self._convert_enum_value(arg_value, actual_type)

        # For other union types, we'll just pass through the value
        return arg_value

    def _convert_list_value(self, arg_value: Any, list_type: Any) -> Any:
        """Convert a value to a list type."""
        if not isinstance(arg_value, list):
            # Try to convert single value to list
            return [arg_value]

        # Already a list, use as-is
        return arg_value

    def _get_friendly_type_name(self, type_hint: Any) -> str:
        """Get a user-friendly name for a type hint."""
        # Handle simple types
        if type_hint in (str, int, float, bool):
            return type_hint.__name__

        # Handle Enums
        if isinstance(type_hint, type) and issubclass(type_hint, Enum):
            return f'enum [{", ".join(str(e.value) for e in type_hint)}]'

        # Handle Union/Optional types
        origin = get_origin(type_hint)
        if origin is Union:
            args = get_args(type_hint)
            # Check if this is Optional[X]
            if type(None) in args and len(args) == 2:
                # Get the non-None type
                actual_type = next(t for t in args if t is not type(None))
                return f'optional {self._get_friendly_type_name(actual_type)}'
            else:
                # Regular Union
                return f'one of [{", ".join(self._get_friendly_type_name(t) for t in args)}]'

        # Handle List types
        if origin in (list, List):
            args = get_args(type_hint)
            if args:
                return f'list of {self._get_friendly_type_name(args[0])}'
            return 'list'

        # Handle Dict types
        if origin in (dict, Dict):
            args = get_args(type_hint)
            if len(args) >= 2:
                return f'dictionary with {self._get_friendly_type_name(args[0])} keys and {self._get_friendly_type_name(args[1])} values'
            return 'dictionary'

        # Default case
        return str(type_hint)
