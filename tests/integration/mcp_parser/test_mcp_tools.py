import random
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import patch

import boto3

from service.handlers.mcp import lambda_handler
from tests.mcp_schemas import JSONRPCResponse
from tests.utils import generate_context, generate_lambda_event


def test_math_tool_add(session_id, table_name):
    """Test math tool with proper session initialization."""
    # Use the session ID from the fixture
    context = generate_context()
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    expected_sum = str(a + b)

    # Call the math tool with the session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '2', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': a, 'b': b}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.OK
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id

    # Validate the response body
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])

    # Verify the basic JSON-RPC structure
    assert lambda_response_body.jsonrpc == '2.0'
    assert lambda_response_body.id == '2'
    assert lambda_response_body.result is not None

    # The result should have a content list
    assert hasattr(lambda_response_body.result, 'content')

    content = lambda_response_body.result.content
    assert len(content) == 1
    assert content[0].text == expected_sum, f'Unexpected response: {content[0].text}'
    assert content[0].type == 'text', f'Unexpected response: {content[0].type}'

    # Now verify the session data in DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Get the session data directly from DynamoDB
    response = table.get_item(Key={'session_id': session_id})

    # Check if the item exists
    assert 'Item' in response, f'Session {session_id} not found in DynamoDB'

    # Verify the session data contains our result
    session_data = response['Item'].get('data', {})
    assert 'result' in session_data, 'Result key not found in session data'
    assert session_data['result'] == Decimal(expected_sum), f'Expected result {expected_sum}, got {session_data["result:"]}'


def test_math_tool_add_error(session_id):
    """Test math tool when logic raises an error."""
    # Use the session ID from the fixture
    context = generate_context()

    # Call the math tool with the session ID
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '3', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 3, 'b': 4}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)

    # Mock the add_two_numbers function to raise an error
    with patch('service.handlers.mcp.add_two_numbers', side_effect=RuntimeError('math error')):
        lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id

    # Validate the error response
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message == 'Error executing tool'
    assert lambda_response_body.error.code == -32603, 'Expected internal error code -32603'


def test_math_tool_invalid_input(session_id):
    """Test math tool with invalid input types."""
    # Use the session ID from the fixture
    context = generate_context()

    # Call the math tool with invalid arguments
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '4', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 'foo', 'b': 4}}}
    event = generate_lambda_event(jsonrpc_payload, session_id=session_id)
    lambda_response = lambda_handler(event, context)

    # Verify the response
    assert lambda_response['statusCode'] == HTTPStatus.BAD_REQUEST
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    assert lambda_response['headers']['MCP-Session-Id'] == session_id

    # Validate the error response
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message == "Invalid value for parameter 'a': invalid literal for int() with base 10: 'foo'"
    assert lambda_response_body.error.code == -32602, 'Expected error code -32602'
