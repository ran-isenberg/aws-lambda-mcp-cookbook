from fastmcp import FastMCP

from service.handlers.utils.observability import logger
from service.logic.math import add_two_numbers

mcp: FastMCP = FastMCP(name='mcp-lambda-server')


@mcp.tool
def math(a: int, b: int) -> int:
    """Add two numbers together"""
    print('in math tool')
    logger.info('using math tool with cool logger', extra={'a': a, 'b': b})
    return add_two_numbers(a, b)


app = mcp.http_app(transport='http', stateless_http=True, json_response=True)
