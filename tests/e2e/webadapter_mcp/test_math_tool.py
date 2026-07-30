import random

import pytest
from mcp import Client


@pytest.mark.asyncio
async def test_math_tool(web_adapter_mcp_url):
    """End-to-end test of the MCP server using the math tool."""
    # Generate two random numbers for testing
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    expected_sum = a + b

    try:
        # Client takes the server URL directly and negotiates the protocol version for us
        async with Client(web_adapter_mcp_url) as client:
            tools_response = await client.list_tools()
            # Verify the math tool is available
            assert 'math' == tools_response.tools[0].name, 'Math tool not found in available tools'

            # Call a tool
            tool_result = await client.call_tool('math', {'a': a, 'b': b})
            # Verify the result
            assert tool_result.content is not None
            assert len(tool_result.content) == 1
            assert tool_result.content[0].text == str(expected_sum), f'Expected {expected_sum}, got {tool_result.content[0].text}'
    except Exception as e:
        pytest.fail(f'End-to-end test failed: {e}')
