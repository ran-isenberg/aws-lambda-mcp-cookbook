"""MCP prompts. Business logic lives in `service.logic.hld`."""

from service.handlers.utils.observability import logger
from service.logic.hld import hld_prompt
from service.mcp_app.mcp_server import mcp


@mcp.prompt(title='Serverless high level design')
def generate_serverless_design_prompt(design_requirements: str) -> str:
    """Generate a serverless design prompt based on the provided design requirements."""
    logger.info('generating serverless design prompt', extra={'design_requirements': design_requirements})
    return hld_prompt(design_requirements)
