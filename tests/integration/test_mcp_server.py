"""Integration tests that drive the real MCP server over the protocol, in-process.

`Client` accepts an `MCPServer` instance directly, so these tests exercise the same
tool/resource/prompt handlers and the same wire types an HTTP client would hit, with no
network, no Lambda and no deployed stack.
"""

import json
import os
import pathlib
import tomllib

import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import LATEST_PROTOCOL_VERSION

from service.app import mcp

# `mcp` comes from the entrypoint on purpose: importing it also imports the handlers package,
# which is what registers the tools, resources and prompts on the server.
from service.mcp_app.context import AppContext, lifespan


@pytest.mark.asyncio
async def test_server_speaks_the_current_protocol():
    async with Client(mcp) as client:
        assert client.protocol_version == LATEST_PROTOCOL_VERSION


@pytest.mark.asyncio
async def test_list_tools():
    async with Client(mcp) as client:
        response = await client.list_tools()

    tool_names = [tool.name for tool in response.tools]
    assert 'math' in tool_names
    math_tool = next(tool for tool in response.tools if tool.name == 'math')
    assert math_tool.description == 'Add two numbers together'
    assert math_tool.input_schema['properties'].keys() == {'a', 'b'}


@pytest.mark.asyncio
async def test_call_math_tool():
    async with Client(mcp) as client:
        result = await client.call_tool('math', {'a': 3, 'b': 4})

    assert result.is_error is False
    assert result.content[0].text == '7'


@pytest.mark.asyncio
async def test_call_math_tool_with_invalid_argument_type():
    async with Client(mcp) as client:
        result = await client.call_tool('math', {'a': 'not-a-number', 'b': 4})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_call_math_tool_with_missing_argument():
    async with Client(mcp) as client:
        result = await client.call_tool('math', {'a': 1})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_call_unknown_tool():
    async with Client(mcp) as client:
        result = await client.call_tool('does_not_exist', {})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_read_profile_resource():
    async with Client(mcp) as client:
        templates = await client.list_resource_templates()
        assert any('users://{user_id}/profile' in t.uri_template for t in templates.resource_templates)

        result = await client.read_resource('users://42/profile')

    assert len(result.contents) == 1
    assert result.contents[0].uri == 'users://42/profile'
    assert 'active' in result.contents[0].text
    assert 'User 42' in result.contents[0].text
    # the handler returns a dict, so the payload really is JSON - say so on the wire
    assert result.contents[0].mime_type == 'application/json'
    assert json.loads(result.contents[0].text) == {'name': 'User 42', 'status': 'active'}


@pytest.mark.asyncio
async def test_get_design_prompt():
    design_requirements = 'Crud API for a serverless orders application'

    async with Client(mcp) as client:
        prompts = await client.list_prompts()
        assert 'generate_serverless_design_prompt' in [prompt.name for prompt in prompts.prompts]

        result = await client.get_prompt('generate_serverless_design_prompt', {'design_requirements': design_requirements})

    assert len(result.messages) == 1
    text = result.messages[0].content.text
    assert text.startswith('You are a serverless Python expert developing on AWS')
    assert design_requirements in text


@pytest.mark.asyncio
async def test_tool_declares_safety_annotations():
    """Clients use these hints to decide what may run without asking the user."""
    async with Client(mcp) as client:
        response = await client.list_tools()

    math_tool = next(tool for tool in response.tools if tool.name == 'math')
    assert math_tool.title == 'Add two numbers'
    assert math_tool.annotations is not None
    assert math_tool.annotations.read_only_hint is True
    assert math_tool.annotations.idempotent_hint is True
    assert math_tool.annotations.open_world_hint is False


@pytest.mark.asyncio
async def test_static_catalog_is_cacheable():
    """The catalog never changes per caller, so clients should not re-list it every turn."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        prompts = await client.list_prompts()
        templates = await client.list_resource_templates()

    for result in (tools, prompts, templates):
        assert result.ttl_ms > 0, 'a ttl of 0 tells clients not to cache at all'
        assert result.cache_scope == 'public'


@pytest.mark.asyncio
async def test_user_scoped_reads_are_not_publicly_cacheable():
    """Profiles differ per user: a shared cache must never serve one user's to another."""
    async with Client(mcp) as client:
        result = await client.read_resource('users://42/profile')

    assert result.cache_scope == 'private'
    assert result.ttl_ms == 0


@pytest.mark.asyncio
async def test_catalog_is_listed_in_deterministic_order():
    """Stable ordering keeps client caches and LLM prompt caches hitting."""
    async with Client(mcp) as client:
        tools = [tool.name for tool in (await client.list_tools()).tools]
        prompts = [prompt.name for prompt in (await client.list_prompts()).prompts]
        templates = [template.name for template in (await client.list_resource_templates()).resource_templates]

    assert tools == sorted(tools)
    assert prompts == sorted(prompts)
    assert templates == sorted(templates)


@pytest.mark.asyncio
async def test_server_identifies_and_describes_itself():
    """instructions is what a client feeds the model about how to use this server."""
    async with Client(mcp) as client:
        assert client.server_info is not None
        assert client.server_info.name == 'mcp-lambda-server'
        assert client.server_info.title == 'AWS Lambda MCP Cookbook'
        assert client.server_info.website_url
        assert client.instructions
        assert 'math' in client.instructions


@pytest.mark.asyncio
async def test_reported_version_matches_the_project_version():
    """The server version is hardcoded because the project is not pip-installed into the Lambda.

    That makes it free to drift from pyproject.toml, so assert the two agree rather than pinning a
    literal here - otherwise this test just needs editing on every release.
    """
    pyproject = tomllib.loads(pathlib.Path('pyproject.toml').read_text())

    async with Client(mcp) as client:
        assert client.server_info is not None
        assert client.server_info.version == pyproject['project']['version']


def test_server_is_wired_to_the_lifespan():
    """Guards the wiring itself: exercising lifespan() directly would pass without it."""
    assert mcp.settings.lifespan is lifespan


@pytest.mark.asyncio
async def test_handler_receives_the_shared_app_context():
    """A handler reaches the lifespan result through ctx.request_context.lifespan_context.

    Built on a throwaway server so the production one keeps its real tool surface, but using the
    same lifespan, so this breaks if that contract changes.
    """
    probe = MCPServer(name='probe', version='1', lifespan=lifespan)
    seen: list[object] = []

    @probe.tool()
    def read_context(ctx: Context) -> str:
        context = ctx.request_context.lifespan_context
        seen.append(context)
        return type(context).__name__

    async with Client(probe) as client:
        result = await client.call_tool('read_context', {})

    assert result.is_error is False
    assert result.content[0].text == 'AppContext'
    assert isinstance(seen[0], AppContext)


@pytest.mark.asyncio
async def test_table_is_resolved_lazily_and_memoised():
    """The table must not be built at startup - that would make TABLE_NAME a boot requirement.

    Constructing a Table resource makes no network call, so this needs no AWS access.
    """
    async with lifespan(mcp) as context:
        assert context._table is None, 'entering the lifespan must not touch DynamoDB or the env'

        table = context.table
        assert table.name == os.environ['TABLE_NAME']
        assert context.table is table, 'the resolved table should be reused, not rebuilt'


@pytest.mark.asyncio
async def test_every_handler_module_is_registered():
    """Guards the split: a handler module missing from handlers/__init__ is silently absent.

    The decorators register on import, so forgetting an import in `service.mcp_app.handlers`
    drops that capability from the catalog without raising anywhere.
    """
    async with Client(mcp) as client:
        tools = await client.list_tools()
        prompts = await client.list_prompts()
        templates = await client.list_resource_templates()

    assert [tool.name for tool in tools.tools] == ['math']
    assert [prompt.name for prompt in prompts.prompts] == ['generate_serverless_design_prompt']
    assert [template.name for template in templates.resource_templates] == ['get_profile']
