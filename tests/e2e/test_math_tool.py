import random

import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from tenacity import retry, stop_after_attempt, wait_fixed


class RetryableAPIError(Exception):
    """Exception raised when an API call fails but should be retried."""

    pass


async def call_math_tool(api_gateway_url, a, b, expected_sum):
    """Call the math tool with retry logic."""
    async with streamablehttp_client(api_gateway_url) as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # Call a tool
            tool_result = await session.call_tool('math', {'a': a, 'b': b})
            # Verify the result
            assert tool_result.content is not None
            assert len(tool_result.content) == 1
            assert tool_result.content[0].text == str(expected_sum), f'Expected {expected_sum}, got {tool_result.content[0].text}'

            # If we get here, the test passed
            print(f'Successfully added {a} + {b} = {expected_sum}')
            return True


@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(3),
    before_sleep=lambda retry_state: print(f'Retrying in 3 seconds... (attempt {retry_state.attempt_number}/5)'),
    reraise=True,
)
async def retry_math_tool_call(api_gateway_url, a, b, expected_sum):
    """Wrapper function with retry logic using tenacity."""
    return await call_math_tool(api_gateway_url, a, b, expected_sum)


@pytest.mark.asyncio
async def test_e2e_math_tool(api_gateway_url):
    """End-to-end test of the MCP server using the math tool."""
    # Generate two random numbers for testing
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    expected_sum = a + b

    try:
        await retry_math_tool_call(api_gateway_url, a, b, expected_sum)
    except Exception as e:
        pytest.fail(f'Failed after retries: {str(e)}')
