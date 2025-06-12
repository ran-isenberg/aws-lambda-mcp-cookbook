import pytest

from cdk.service.constants import APIGATEWAY, GW_RESOURCE
from tests.utils import get_stack_output


@pytest.fixture(scope='module', autouse=True)
def api_gateway_url():
    # Given: The API Gateway URL
    return f'{get_stack_output(APIGATEWAY)}{GW_RESOURCE}'
