from aws_lambda_env_modeler import init_environment_variables
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.models.env_vars import McpHandlerEnvVars
from service.handlers.utils.authentication import authenticate
from service.handlers.utils.mcp import mcp
from service.handlers.utils.observability import logger, metrics, tracer
from service.logic.math import add_two_numbers


@mcp.tool()
def math(a: int, b: int) -> int:
    """Add two numbers together"""
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError('Invalid input: a and b must be integers')

    result = add_two_numbers(a, b)
    metrics.add_metric(name='ValidMcpEvents', unit=MetricUnit.Count, value=1)
    return result


@init_environment_variables(model=McpHandlerEnvVars)
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    authenticate(event, context)
    return mcp.handle_request(event, context)
