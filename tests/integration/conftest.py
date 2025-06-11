import os

import pytest

from cdk.service.constants import (
    POWER_TOOLS_LOG_LEVEL,
    POWERTOOLS_SERVICE_NAME,
    SERVICE_NAME,
    TABLE_NAME_OUTPUT,
)
from service.handlers.mcp import lambda_handler
from tests.utils import generate_context, get_stack_output, initialize_mcp_session, terminate_mcp_session


@pytest.fixture(scope='module', autouse=True)
def init():
    os.environ[POWERTOOLS_SERVICE_NAME] = SERVICE_NAME
    os.environ[POWER_TOOLS_LOG_LEVEL] = 'DEBUG'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['TABLE_NAME'] = get_stack_output(TABLE_NAME_OUTPUT)


@pytest.fixture(scope='module', autouse=True)
def table_name():
    return os.environ['TABLE_NAME']


@pytest.fixture(scope='function')
def session_id():
    # Initialize an MCP session
    context = generate_context()
    session_id = initialize_mcp_session(lambda_handler, context)

    # Yield the session ID for the test to use
    yield session_id

    # Clean up by terminating the session
    terminate_mcp_session(lambda_handler, session_id, context)
