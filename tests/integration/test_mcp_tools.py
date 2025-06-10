from http import HTTPStatus
from unittest.mock import patch

from service.handlers.mcp import lambda_handler
from tests.mcp_schemas import JSONRPCResponse
from tests.utils import generate_context, generate_lambda_event


def test_math_tool_add():
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '2', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 3, 'b': 4}}}
    event = generate_lambda_event(jsonrpc_payload)
    lambda_response = lambda_handler(event, generate_context())
    assert lambda_response['statusCode'] == HTTPStatus.OK
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.result.content[0].text == '7', f'Unexpected response: {lambda_response_body.result.content[0].text}'
    assert lambda_response_body.result.content[0].type == 'text', f'Unexpected response: {lambda_response_body.result.content[0].type}'
    assert len(lambda_response_body.result.content) == 1


def test_math_tool_add_error():
    """Test math tool when logic raises an error."""
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '3', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 3, 'b': 4}}}
    event = generate_lambda_event(jsonrpc_payload)
    with patch('service.handlers.mcp.add_two_numbers', side_effect=RuntimeError('math error')):
        lambda_response = lambda_handler(event, generate_context())
    assert lambda_response['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message == 'Error executing tool: math error'


def test_math_tool_invalid_input():
    """Test math tool with invalid input types."""
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '4', 'method': 'tools/call', 'params': {'name': 'math', 'arguments': {'a': 'foo', 'b': 4}}}
    event = generate_lambda_event(jsonrpc_payload)
    lambda_response = lambda_handler(event, generate_context())
    assert lambda_response['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message == 'Error executing tool: Invalid input: a and b must be integers'


def test_tool_not_found():
    """Test calling a non-existent tool returns 404."""
    jsonrpc_payload = {'jsonrpc': '2.0', 'id': '5', 'method': 'tools/call', 'params': {'name': 'not_a_tool', 'arguments': {'a': 1, 'b': 2}}}
    event = generate_lambda_event(jsonrpc_payload)
    lambda_response = lambda_handler(event, generate_context())
    assert lambda_response['statusCode'] == HTTPStatus.NOT_FOUND
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.error.message.startswith("Tool 'not_a_tool' not found")
