import json
import random
import string
from http import HTTPStatus
from typing import List, Optional

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel

from cdk.service.utils import get_stack_name


def generate_random_string(length: int = 3):
    letters = string.ascii_letters
    random_string = ''.join(random.choice(letters) for _ in range(length))
    return random_string


def generate_context() -> LambdaContext:
    context = LambdaContext()
    context._aws_request_id = '888888'
    context._function_name = 'test'
    context._memory_limit_in_mb = 128
    context._invoked_function_arn = 'arn:aws:lambda:eu-west-1:123456789012:function:test'
    return context


def get_stack_output(output_key: str) -> str:
    client = boto3.client('cloudformation')
    response = client.describe_stacks(StackName=get_stack_name())
    stack_outputs = response['Stacks'][0]['Outputs']
    for value in stack_outputs:
        if str(value['OutputKey']) == output_key:
            return value['OutputValue']
    raise Exception(f'stack output {output_key} was not found')


class ContentItem(BaseModel):
    type: str
    text: str


class Result(BaseModel):
    content: List[ContentItem]


class JSONRPCErrorModel(BaseModel):
    code: int
    message: str


class ErrorContentItem(BaseModel):
    type: str
    text: str


class JSONRPCResponse(BaseModel):
    jsonrpc: str
    id: Optional[str]
    result: Optional[Result] = None
    error: Optional[JSONRPCErrorModel] = None
    errorContent: Optional[List[ErrorContentItem]] = None


def generate_lambda_event(jsonrpc_payload: dict, session_id: Optional[str] = None):
    """Create a realistic API Gateway proxy event for Lambda.

    Args:
        jsonrpc_payload: The JSON-RPC payload to include in the request body
        session_id: Optional session ID to include in the headers. If None, no session ID is included.
    """
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json, text/event-stream',
    }

    multi_value_headers = {
        'content-type': ['application/json'],
        'accept': ['application/json, text/event-stream'],
    }

    if session_id:
        headers['mcp-session-id'] = session_id
        multi_value_headers['mcp-session-id'] = [session_id]

    return {
        'resource': '/mcp',
        'path': '/mcp',
        'httpMethod': 'POST',
        'headers': headers,
        'multiValueHeaders': multi_value_headers,
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': None,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': '/mcp',
            'httpMethod': 'POST',
            'path': '/Prod/mcp',
            'identity': {},
            'requestId': 'test-request-id',
        },
        'body': json.dumps(jsonrpc_payload),
        'isBase64Encoded': False,
    }


def initialize_mcp_session(lambda_handler_func, context=None):
    """Initialize an MCP session and return the session ID.

    Args:
        lambda_handler_func: The Lambda handler function to call
        context: Optional Lambda context object. If None, one will be created.

    Returns:
        The session ID from the initialize response
    """
    if context is None:
        context = generate_context()

    # Create an initialize request
    init_payload = {'jsonrpc': '2.0', 'id': '1', 'method': 'initialize'}

    # Call the lambda handler with the initialize request
    event = generate_lambda_event(init_payload)
    response = lambda_handler_func(event, context)

    # Verify response and extract session ID
    assert response['statusCode'] == HTTPStatus.OK
    assert 'MCP-Session-Id' in response['headers']

    return response['headers']['MCP-Session-Id']


def terminate_mcp_session(lambda_handler_func, session_id, context=None):
    """Terminate an MCP session by sending a DELETE request.

    Args:
        lambda_handler_func: The Lambda handler function to call
        session_id: The session ID to terminate
        context: Optional Lambda context object. If None, one will be created.

    Returns:
        Boolean indicating if the termination was successful
    """
    if context is None:
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

    # Call the lambda handler with the DELETE request
    response = lambda_handler_func(event, context)

    # Verify the response indicates successful deletion
    return response['statusCode'] == HTTPStatus.NO_CONTENT
