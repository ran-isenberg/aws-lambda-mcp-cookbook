"""MCP resources. Business logic lives in `service.logic.profiles`."""

from service.handlers.utils.observability import logger
from service.logic.profiles import get_profile_by_id
from service.mcp_app.mcp_server import mcp


# Dynamic resource template. mime_type is explicit because the handler returns a dict, which the
# SDK serializes to JSON - without it the payload is announced as text/plain.
@mcp.resource('users://{user_id}/profile', title='User profile', mime_type='application/json')
def get_profile(user_id: int) -> dict[str, str]:
    """Fetch user profile by user ID."""
    logger.info('fetching user profile', extra={'user_id': user_id})
    return get_profile_by_id(user_id)
