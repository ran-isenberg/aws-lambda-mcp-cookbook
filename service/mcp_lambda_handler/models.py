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

"""Models for the MCP Lambda handler."""

from enum import Enum
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from service.mcp_lambda_handler.constants import CONTENT_TYPE_JSON


class MCPMethod(str, Enum):
    """Enum for MCP JSON-RPC methods."""

    INITIALIZE = 'initialize'
    NOTIFICATION = 'notification'
    TOOLS_LIST = 'tools/list'
    TOOLS_CALL = 'tools/call'
    PING = 'ping'


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request model."""

    jsonrpc: Literal['2.0']
    id: Optional[Union[str, int]] = Field(None, description='Request identifier')
    method: Optional[MCPMethod] = Field(..., description='Method to be invoked')
    params: Optional[Union[Dict[str, Any], list]] = Field(None, description='Method parameters')

    @field_validator('method', mode='before')
    def validate_method(cls, v: str) -> MCPMethod:
        """Validate and convert method to MCPMethod enum."""
        if v is None:
            raise ValueError('Method is required')
        if v.startswith('notifications/'):
            return MCPMethod.NOTIFICATION
        try:
            return MCPMethod(v)
        except Exception as e:
            raise ValueError(f'Invalid method: {v}. Must be one of {list(MCPMethod)}') from e


class McpApiGatewayProxyEventHeaders(BaseModel):
    """Headers model for the MCP API Gateway event with case-insensitive lookup."""

    content_type: str = Field(str, min_length=1, alias='content-type', description='Content-Type header')
    mcp_session_id: Optional[str] = Field(None, alias='mcp-session-id')
    mcp_version: Optional[str] = Field(None, alias='mcp-version')

    @model_validator(mode='before')
    @classmethod
    def convert_headers_to_lowercase(cls, data: Dict) -> Dict:
        """Convert all header keys to lowercase for case-insensitive comparison."""
        if isinstance(data, dict):
            return {k.lower() if isinstance(k, str) else k: v for k, v in data.items()}
        return data


# Base class for API Gateway events
class MCPAPIGatewayProxyEventBase(BaseModel):
    """Base API Gateway event model with common fields."""

    headers: McpApiGatewayProxyEventHeaders
    httpMethod: str

    @property
    def mcp_session_id(self) -> Optional[str]:
        """Get the MCP session ID from headers."""
        return self.headers.mcp_session_id if self.headers else None

    @property
    def is_content_type_json(self) -> bool:
        """Check if the content type is JSON."""
        return self.headers.content_type == CONTENT_TYPE_JSON


# POST specific model - requires a JSON-RPC body
class MCPPostAPIGatewayProxyEvent(MCPAPIGatewayProxyEventBase):
    """API Gateway event model for POST requests with JSON-RPC body."""

    body: JSONRPCRequest
    httpMethod: Literal['POST'] = Field(..., description='HTTP method must be POST for JSON-RPC requests')

    @field_validator('body', mode='before')
    def parse_body(cls, v) -> JSONRPCRequest:
        """Parse the body as a JSON-RPC request."""
        if v is None:
            raise ValueError('Body is required for POST requests')
        return JSONRPCRequest.model_validate_json(v)


# DELETE specific model - no body required
class MCPDeleteAPIGatewayProxyEvent(MCPAPIGatewayProxyEventBase):
    """API Gateway event model for DELETE requests (session termination)."""

    body: Optional[str] = Field(None, description='Body is not required for DELETE requests')
    httpMethod: Literal['DELETE'] = Field(..., description='HTTP method must be DELETE for session termination')
