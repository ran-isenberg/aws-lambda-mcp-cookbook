from service.mcp_lambda_handler.mcp_lambda_handler import MCPLambdaHandler

mcp = MCPLambdaHandler(name='mcp-lambda-server', version='1.0.0')


@mcp.tool()
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def lambda_handler(event, context):
    return mcp.handle_request(event, context)
