import os

import pytest

from cdk.service.constants import POWER_TOOLS_LOG_LEVEL, POWERTOOLS_SERVICE_NAME, SERVICE_NAME


@pytest.fixture(scope='module', autouse=True)
def init():
    os.environ[POWERTOOLS_SERVICE_NAME] = SERVICE_NAME
    os.environ[POWER_TOOLS_LOG_LEVEL] = 'DEBUG'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    # The server's lifespan resolves this to build the shared boto3 resource. Constructing a
    # boto3 Table makes no network call, so these tests still need no AWS access.
    os.environ.setdefault('TABLE_NAME', 'integration-test-table')
