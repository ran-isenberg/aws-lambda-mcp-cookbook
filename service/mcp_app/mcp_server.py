"""The MCP server object and its identity.

Importing this module gives you a server with **no capabilities registered**. The tools, resources
and prompts live in `service.mcp_app.handlers` and register themselves on import - see that
package's docstring. Import `service.app` if you want the fully assembled server.
"""

from mcp.server import MCPServer

from service.mcp_app.caching import CACHE_HINTS
from service.mcp_app.context import lifespan

SERVER_INSTRUCTIONS = """\
A sample serverless MCP server. Use the 'math' tool to add two integers. Read
'users://{user_id}/profile' to look up a user by numeric id. Use the
'generate_serverless_design_prompt' prompt to turn a set of requirements into a serverless
high level design brief."""


class DeterministicMCPServer(MCPServer):
    """Serves the catalog in a stable, name-sorted order.

    The 2026-07-28 spec asks servers to list in a deterministic order so clients can cache the
    result and LLM prompt caches keep hitting. Registration order is already stable per
    deployment; sorting keeps it stable even as capabilities are added or moved between modules.
    """

    async def list_tools(self):
        return sorted(await super().list_tools(), key=lambda tool: tool.name)

    async def list_prompts(self):
        return sorted(await super().list_prompts(), key=lambda prompt: prompt.name)

    async def list_resource_templates(self):
        return sorted(await super().list_resource_templates(), key=lambda template: template.name)


mcp: MCPServer = DeterministicMCPServer(
    name='mcp-lambda-server',
    title='AWS Lambda MCP Cookbook',
    description='serverless MCP server blueprint.',
    instructions=SERVER_INSTRUCTIONS,
    website_url='https://github.com/ran-isenberg/aws-lambda-mcp-cookbook',
    version='4.0.0',
    lifespan=lifespan,
    cache_hints=CACHE_HINTS,
)
