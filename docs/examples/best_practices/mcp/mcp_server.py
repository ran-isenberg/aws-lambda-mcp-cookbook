from fastmcp import FastMCP

from service.handlers.utils.observability import logger
from service.logic.prompts.hld import hld_prompt
from service.logic.resources.profiles import get_profile_by_id
from service.logic.tools.math import add_two_numbers

mcp: FastMCP = FastMCP(name='mcp-lambda-server')


@mcp.tool
def math(a: int, b: int) -> int:
    """Add two numbers together"""
    logger.info('using math tool', extra={'a': a, 'b': b})
    return add_two_numbers(a, b)


# Dynamic resource template
@mcp.resource('users://{user_id}/profile')
def get_profile(user_id: int) -> dict[str, str]:
    """Fetch user profile by user ID."""
    logger.info('fetching user profile', extra={'user_id': user_id})
    return get_profile_by_id(user_id)


@mcp.prompt()
def generate_serverless_design_prompt(design_requirements: str) -> str:
    """Generate a serverless design prompt based on the provided design requirements."""
    logger.info('generating serverless design prompt', extra={'design_requirements': design_requirements})
    return hld_prompt(design_requirements)


app = mcp.http_app(transport='http', stateless_http=True, json_response=True)
