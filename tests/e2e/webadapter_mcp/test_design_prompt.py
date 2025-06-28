import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@pytest.mark.asyncio
async def test_hld_prompt(web_adapter_mcp_url):
    """End-to-end test of the MCP server using the hld prompt tool."""
    try:
        design_requirements = 'Crud API for a serverless orders application'
        expected_start_text = 'You are a serverless Python expert developing on AWS'
        async with streamablehttp_client(web_adapter_mcp_url) as (
            read_stream,
            write_stream,
            _,
        ):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                prompts_list_response = await session.list_prompts()
                # Verify the hld prompt is available
                assert 'generate_serverless_design_prompt' == prompts_list_response.prompts[0].name, 'HLD prompt not found in available prompts'

                # Call a prompt
                prompt_result = await session.get_prompt('generate_serverless_design_prompt', {'design_requirements': design_requirements})
                # Verify the result
                assert prompt_result.messages[0] is not None, 'Prompt result should not be None'
                assert len(prompt_result.messages) == 1, 'Prompt result should contain exactly one message'
                result = prompt_result.messages[0].content.text
                assert isinstance(result, str), 'Prompt result should be a string'
                assert result.lower().startswith(expected_start_text.lower()), 'Prompt result should start with expected text'
                assert design_requirements.lower() in result.lower(), 'Prompt result should contain "design_requirements" in the response'
    except Exception as e:
        pytest.fail(f'End-to-end test failed: {e}')
