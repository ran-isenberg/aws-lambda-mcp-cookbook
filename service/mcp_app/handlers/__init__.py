"""Every MCP capability this server exposes.

The SDK's `@mcp.tool()`, `@mcp.resource()` and `@mcp.prompt()` decorators register on import, so a
capability only reaches `tools/list` if its module is imported. Importing this package imports all
of them - this is the single place responsible for that, which is why the names below are
re-exported rather than dropped as unused.

Adding a capability means adding a module here and an import below. Forgetting the import makes the
handler silently absent from the catalog rather than raising, so the listing tests in
`tests/integration/test_mcp_server.py` are what catch it.
"""

from service.mcp_app.handlers import prompts, resources, tools

__all__ = ['prompts', 'resources', 'tools']
