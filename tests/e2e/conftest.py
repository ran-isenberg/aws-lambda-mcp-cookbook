import pytest

from cdk.service.constants import PURE_MCP_API_URL, WEB_ADAPTER_MCP_API_URL
from tests.utils import get_stack_output


@pytest.fixture(scope='module', autouse=False)
def web_adapter_mcp_url():
    return f'{get_stack_output(WEB_ADAPTER_MCP_API_URL)}'


@pytest.fixture(scope='module', autouse=False)
def pure_lambda_mcp_url():
    return f'{get_stack_output(PURE_MCP_API_URL)}'
