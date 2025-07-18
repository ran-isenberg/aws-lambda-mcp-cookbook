from http import HTTPStatus

from service.handlers.mcp import lambda_handler
from tests.mcp_schemas import JSONRPCResponse
from tests.utils import generate_context, generate_lambda_event


def test_tool_not_found(session_id):
    """Test calling a non-existent tool returns 404."""
    # First initialize a session
    context = generate_context()

    # Then call a non-existent tool with the session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '5', 'method': 'tools/call', 'params': {'name': 'not_a_tool', 'arguments': {'a': 1, 'b': 2}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.NOT_FOUND
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id

    # Validate the error response
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message.startswith("Tool 'not_a_tool' not found")


def test_initialize_method():
    """Test the initialize method creates a session and returns expected capabilities."""
    # Create an initialize request
    init_payload = {'jsonrpc': '2.0', 'id': '1', 'method': 'initialize'}

    # Call the lambda handler with the initialize request
    context = generate_context()
    event = generate_lambda_event(init_payload)
    lambda_response = lambda_handler(event, context)

    # Verify response status and headers
    assert lambda_response['statusCode'] == HTTPStatus.OK
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert 'MCP-Session-Id' in lambda_response['headers']


def test_tools_list_method(session_id):
    """Test the tools/list method returns available tools with a valid session."""
    # First initialize a session
    context = generate_context()

    # Then call tools/list with the session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '2', 'method': 'tools/list'}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.OK
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id

    # Validate the response body using direct JSON parsing
    import json

    response_json = json.loads(lambda_response['body'])

    # Verify the basic JSON-RPC structure
    assert response_json['jsonrpc'] == '2.0'
    assert response_json['id'] == '2'
    assert 'result' in response_json

    # Verify the tools list
    assert 'tools' in response_json['result']
    tools = response_json['result']['tools']
    assert isinstance(tools, list)
    assert len(tools) > 0

    # Find the math tool in the list
    math_tool = None
    for tool in tools:
        if tool.get('name') == 'math':
            math_tool = tool
            break

    # Verify math tool exists and has expected properties
    assert math_tool is not None, 'Math tool not found in tools list'
    assert 'description' in math_tool
    assert math_tool['description'] == 'Add two numbers together'
    assert 'inputSchema' in math_tool
    assert 'type' in math_tool['inputSchema']
    assert math_tool['inputSchema']['type'] == 'object'
    assert 'properties' in math_tool['inputSchema']

    # Verify math tool parameters
    properties = math_tool['inputSchema']['properties']
    assert 'a' in properties
    assert 'b' in properties
    assert properties['a']['type'] == 'integer'
    assert properties['b']['type'] == 'integer'


def test_invalid_session():
    """Test that using an invalid session ID returns a 404 error."""
    # Create a request with an invalid session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '6', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}}
    event = generate_lambda_event(jsonrpc_payload, session_id='invalid-session-id')

    # Call the lambda handler
    context = generate_context()
    lambda_response = lambda_handler(event, context)

    # Verify the response indicates an invalid session
    assert lambda_response['statusCode'] == HTTPStatus.NOT_FOUND.value
    assert lambda_response['headers']['Content-Type'] == 'application/json'

    # Validate the error message
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.code == -32000
    assert lambda_response_body.error.message == 'Invalid or expired session'


def test_missing_session():
    """Test that session requirement is enforced."""
    # Create a request without a session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '7', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=None)

    # Call the lambda handler
    context = generate_context()
    lambda_response = lambda_handler(event, context)

    # Verify the response indicates a session is required
    assert lambda_response['statusCode'] == HTTPStatus.BAD_REQUEST.value
    assert lambda_response['headers']['Content-Type'] == 'application/json'

    # Validate the error message
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.code == -32600
    assert lambda_response_body.error.message == 'Session required'


def test_session_deletion(session_id):
    """Test that a session can be properly deleted."""
    # First initialize a session
    context = generate_context()

    # Create a DELETE request to remove the session
    event = {
        'resource': '/mcp',
        'path': '/mcp',
        'httpMethod': 'DELETE',
        'headers': {'content-type': 'application/json', 'accept': 'application/json', 'mcp-session-id': session_id},
        'multiValueHeaders': {'content-type': ['application/json'], 'accept': ['application/json'], 'mcp-session-id': [session_id]},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': None,
        'stageVariables': None,
        'requestContext': {'resourcePath': '/mcp', 'httpMethod': 'DELETE', 'path': '/Prod/mcp', 'identity': {}, 'requestId': 'test-delete-request'},
        'body': None,
        'isBase64Encoded': False,
    }

    # Call the lambda handler
    lambda_response = lambda_handler(event, context)

    # Verify the response indicates successful deletion
    assert lambda_response['statusCode'] == HTTPStatus.NO_CONTENT.value

    # Now try to use the deleted session
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '8', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response indicates an invalid session
    assert lambda_response['statusCode'] == HTTPStatus.NOT_FOUND.value
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message == 'Invalid or expired session'


def test_jsonrpc_notification(session_id):
    """Test handling of JSON-RPC notification (request without an ID)."""
    # First initialize a session
    context = generate_context()

    # Create a notification (request without an ID)
    jsonrpc_payload = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Notifications should return 202 Accepted per MCP spec
    assert lambda_response['statusCode'] == HTTPStatus.ACCEPTED.value
    assert lambda_response['body'] == ''
    assert 'Content-Type' in lambda_response['headers']
    assert 'MCP-Version' in lambda_response['headers']


def test_invalid_jsonrpc_structure(session_id):
    """Test handling of invalid JSON-RPC requests."""
    # Test cases for invalid JSON-RPC structures
    invalid_cases = [
        # Missing 'jsonrpc' field
        {'id': '9', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}},
        # Wrong jsonrpc version
        {'jsonrpc': '1.0', 'id': '10', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}},
        # Missing 'method' field
        {'jsonrpc': '2.0', 'id': '11', 'params': {'name': 'math', 'arguments': {'a': 1, 'b': 2}}},
    ]

    context = generate_context()

    for i, invalid_payload in enumerate(invalid_cases):
        # Generate event with invalid payload
        event = generate_lambda_event(invalid_payload, session_id=session_id)
        lambda_response = lambda_handler(event, context)

        # Verify the response indicates parse error
        assert lambda_response['statusCode'] == HTTPStatus.BAD_REQUEST.value, f'Case {i} failed with status {lambda_response["statusCode"]}'
        lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
        assert lambda_response_body.error.code == -32600
        assert lambda_response_body.error.message == 'Parse error'


def test_malformed_json():
    """Test handling of malformed JSON in the request body."""
    # Create an event with invalid JSON in the body
    event = {
        'resource': '/mcp',
        'path': '/mcp',
        'httpMethod': 'POST',
        'headers': {'content-type': 'application/json', 'accept': 'application/json'},
        'multiValueHeaders': {'content-type': ['application/json'], 'accept': ['application/json']},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': None,
        'stageVariables': None,
        'requestContext': {'resourcePath': '/mcp', 'httpMethod': 'POST', 'path': '/Prod/mcp', 'identity': {}, 'requestId': 'test-invalid-json'},
        'body': '{invalid json here',
        'isBase64Encoded': False,
    }

    # Call the lambda handler
    context = generate_context()
    lambda_response = lambda_handler(event, context)

    # Verify the response indicates a JSON parse error
    assert lambda_response['statusCode'] == HTTPStatus.BAD_REQUEST.value
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.code == -32600
    assert lambda_response_body.error.message == 'Parse error'


def test_ping_method(session_id):
    """Test the ping method returns success with a valid session."""
    # First initialize a session
    context = generate_context()

    # Then call the ping method with the session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '12', 'method': 'ping'}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.OK.value
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id
