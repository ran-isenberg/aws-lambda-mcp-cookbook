import os

import pytest

from cdk.service.constants import (
    POWER_TOOLS_LOG_LEVEL,
    POWERTOOLS_SERVICE_NAME,
    SERVICE_NAME,
    TABLE_NAME_OUTPUT,
)
from tests.utils import get_stack_output


@pytest.fixture(scope='module', autouse=True)
def init():
    os.environ[POWERTOOLS_SERVICE_NAME] = SERVICE_NAME
    os.environ[POWER_TOOLS_LOG_LEVEL] = 'DEBUG'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'  # used for appconfig mocked boto calls
    os.environ['TABLE_NAME'] = get_stack_output(TABLE_NAME_OUTPUT)


@pytest.fixture(scope='module', autouse=True)
def table_name():
    return os.environ['TABLE_NAME']
