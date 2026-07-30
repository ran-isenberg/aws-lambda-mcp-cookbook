"""MCP tools. Business logic lives in `service.logic.math`."""

from mcp.types import ToolAnnotations

from service.handlers.utils.observability import logger
from service.logic.math import add_two_numbers
from service.mcp_app.mcp_server import mcp


@mcp.tool(
    title='Add two numbers',
    annotations=ToolAnnotations(
        read_only_hint=True,  # touches no state, so clients may auto-approve it
        idempotent_hint=True,  # same arguments always produce the same answer
        open_world_hint=False,  # pure computation, no external systems
    ),
)
def math(a: int, b: int) -> int:
    """Add two numbers together"""
    logger.info('using math tool', extra={'a': a, 'b': b})
    return add_two_numbers(a, b)
