from typing import List, Optional

from pydantic import BaseModel

from service.handlers.mcp import lambda_handler
from tests.utils import generate_context


class ContentItem(BaseModel):
    type: str
    text: str


class Result(BaseModel):
    content: List[ContentItem]


class JSONRPCResponse(BaseModel):
    jsonrpc: str
    id: Optional[str]
    result: Result


event = {
    'resource': '/',
    'path': '/',
    'httpMethod': 'POST',
    'headers': {
        'accept': 'application/json',
        'content-type': 'application/json',
        'host': 'your-api-id.execute-api.us-east-1.amazonaws.com',
        'user-agent': 'curl/8.0.1',
        'x-forwarded-for': '203.0.113.42',
        'x-forwarded-port': '443',
        'x-forwarded-proto': 'https',
        'mcp-session-id': 'sess-abc123',
    },
    'multiValueHeaders': {
        'accept': ['application/json'],
        'content-type': ['application/json'],
        'host': ['your-api-id.execute-api.us-east-1.amazonaws.com'],
        'user-agent': ['curl/8.0.1'],
        'x-forwarded-for': ['203.0.113.42'],
        'x-forwarded-port': ['443'],
        'x-forwarded-proto': ['https'],
        'mcp-session-id': ['sess-abc123'],
    },
    'queryStringParameters': None,
    'multiValueQueryStringParameters': None,
    'pathParameters': None,
    'stageVariables': None,
    'requestContext': {
        'accountId': '123456789012',
        'resourceId': 'abc123',
        'stage': 'prod',
        'requestId': 'req-456',
        'identity': {'sourceIp': '203.0.113.42', 'userAgent': 'curl/8.0.1'},
        'resourcePath': '/',
        'httpMethod': 'POST',
        'apiId': 'your-api-id',
    },
    'body': '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"getWeather","arguments":{"city":"zubi"}}}',
    'isBase64Encoded': False,
}


def test_int():
    lambda_response = lambda_handler(event, generate_context())
    assert lambda_response['statusCode'] == 200
    assert lambda_response['headers']['Content-Type'] == 'application/json'
    lambda_response_body = JSONRPCResponse.model_validate_json(lambda_response['body'])
    assert lambda_response_body.result.content[0].text == 'The weather in zubi is sunny and 72°F.', (
        f'Unexpected response: {lambda_response_body.result.content[0].text}'
    )
    print(lambda_response_body.model_dump_json())
