import random

import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@pytest.mark.asyncio
async def test_e2e_math_tool(api_gateway_url):
    """End-to-end test of the MCP server using the math tool."""
    # Generate two random numbers for testing
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    expected_sum = a + b

    async with streamablehttp_client(api_gateway_url) as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            tools_response = await session.list_tools()
            # Verify the math tool is available
            assert 'math' == tools_response.tools[0].name, 'Math tool not found in available tools'

            # Call a tool
            tool_result = await session.call_tool('math', {'a': a, 'b': b})
            # Verify the result
            assert tool_result.content is not None
            assert len(tool_result.content) == 1
            assert tool_result.content[0].text == str(expected_sum), f'Expected {expected_sum}, got {tool_result.content[0].text}'
            await session.send_ping()
