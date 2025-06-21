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

"""Constants for the MCP Lambda handler."""

# Constants for JSON-RPC methods
METHOD_INITIALIZE = 'initialize'
METHOD_TOOLS_LIST = 'tools/list'
METHOD_TOOLS_CALL = 'tools/call'
METHOD_PING = 'ping'

# Constants for HTTP methods
HTTP_METHOD_DELETE = 'DELETE'
HTTP_METHOD_GET = 'GET'
HTTP_METHOD_POST = 'POST'

# Constants for content types
CONTENT_TYPE_JSON = 'application/json'

# Constants for MCP protocol
MCP_VERSION = '0.6'
MCP_PROTOCOL_VERSION = '2024-11-05'

# Constants for error codes
# Standard JSON-RPC 2.0 Error Codes
ERROR_PARSE = -32700  # Parse error - Invalid JSON was received by the server
ERROR_INVALID_REQUEST = -32600  # Invalid Request - The JSON sent is not a valid Request object
ERROR_METHOD_NOT_FOUND = -32601  # Method not found - The method does not exist/is not available
ERROR_INVALID_PARAMS = -32602  # Invalid params - Invalid method parameter(s)
ERROR_INTERNAL = -32603  # Internal error - A generic internal error occurred on the server

# MCP Specific Error Codes
ERROR_REQUEST_CANCELLED = -32800  # Request cancelled - The request was cancelled by the client or server
ERROR_CONTENT_TOO_LARGE = -32801  # Content too large - The request or response payload exceeded the allowed size

# Implementation-defined server errors (reserved range: -32000 to -32099)
ERROR_SERVER = -32000  # Generic server error
