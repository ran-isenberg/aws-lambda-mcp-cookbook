import pytest

from cdk.service.constants import WEB_ADAPTER_MCP_API_URL
from tests.utils import get_stack_output


@pytest.fixture(scope='module', autouse=False)
def web_adapter_mcp_url():
    return f'{get_stack_output(WEB_ADAPTER_MCP_API_URL)}'
