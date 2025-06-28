import random

import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl


@pytest.mark.asyncio
async def test_user_resource(web_adapter_mcp_url):
    """End-to-end test of the MCP server using the user profile resource template."""
    a = random.randint(1, 100)
    expected_uri = AnyUrl(f'users://{a}/profile')

    try:
        async with streamablehttp_client(web_adapter_mcp_url) as (
            read_stream,
            write_stream,
            _,
        ):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                resource_temp_list = await session.list_resource_templates()
                # Verify the user profile resource is available
                assert any(
                    'users://{user_id}/profile' in resource_template.uriTemplate for resource_template in resource_temp_list.resourceTemplates
                ), 'User profile resource not found in available resources'

                # Call a resource template
                resource_result = await session.read_resource(expected_uri)
                # Verify the result
                assert resource_result.contents is not None
                assert len(resource_result.contents) == 1
                assert 'status' in resource_result.contents[0].text, (
                    f'Expected user profile content to contain status, got: {resource_result.content[0].text}'
                )
                assert resource_result.contents[0].uri == expected_uri, (
                    f'Expected resource URI to be {expected_uri}, got: {resource_result.contents[0].uri}'
                )

    except Exception as e:
        pytest.fail(f'End-to-end test failed: {e}')
