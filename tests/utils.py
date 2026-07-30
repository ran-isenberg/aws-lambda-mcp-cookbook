import random
import string

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

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
