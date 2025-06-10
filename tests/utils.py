import json
import random
import string
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


def generate_lambda_event(jsonrpc_payload: dict):
    """Create a realistic API Gateway proxy event for Lambda."""
    return {
        'resource': '/mcp',
        'path': '/mcp',
        'httpMethod': 'POST',
        'headers': {
            'content-type': 'application/json',
            'accept': 'application/json, text/event-stream',
        },
        'multiValueHeaders': {
            'content-type': ['application/json'],
            'accept': ['application/json, text/event-stream'],
        },
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
