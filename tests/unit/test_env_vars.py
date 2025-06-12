import pytest
from pydantic import ValidationError

from service.handlers.models.env_vars import McpHandlerEnvVars, Observability


def test_missing_required_fields():
    # Given: Required fields are missing
    with pytest.raises(ValidationError):
        McpHandlerEnvVars()


def test_missing_table_name():
    # Given: TABLE_NAME is missing but observability fields are present
    with pytest.raises(ValidationError):
        McpHandlerEnvVars(POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL='INFO')


def test_missing_observability_fields():
    # Given: TABLE_NAME is present but observability fields are missing
    with pytest.raises(ValidationError):
        McpHandlerEnvVars(TABLE_NAME='my-table')


def test_empty_table_name():
    # Given: TABLE_NAME is empty
    with pytest.raises(ValidationError):
        McpHandlerEnvVars(TABLE_NAME='', POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL='INFO')


def test_empty_service_name():
    # Given: POWERTOOLS_SERVICE_NAME is empty
    with pytest.raises(ValidationError):
        McpHandlerEnvVars(TABLE_NAME='my-table', POWERTOOLS_SERVICE_NAME='', LOG_LEVEL='INFO')


def test_invalid_log_level():
    # Given: LOG_LEVEL has invalid value
    with pytest.raises(ValidationError):
        McpHandlerEnvVars(TABLE_NAME='my-table', POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL='INVALID')


def test_valid_env_vars():
    # Given: All required fields are valid
    env = McpHandlerEnvVars(TABLE_NAME='my-table', POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL='INFO')
    assert env.TABLE_NAME == 'my-table'
    assert env.POWERTOOLS_SERVICE_NAME == 'test-service'
    assert env.LOG_LEVEL == 'INFO'


def test_observability_vars():
    # Given: Valid observability settings
    obs_vars = Observability(POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL='DEBUG')
    assert obs_vars.POWERTOOLS_SERVICE_NAME == 'test-service'
    assert obs_vars.LOG_LEVEL == 'DEBUG'


def test_observability_all_log_levels():
    # Given: All valid log levels
    valid_log_levels = ['DEBUG', 'INFO', 'ERROR', 'CRITICAL', 'WARNING', 'EXCEPTION']

    for level in valid_log_levels:
        obs = Observability(POWERTOOLS_SERVICE_NAME='test-service', LOG_LEVEL=level)
        assert obs.LOG_LEVEL == level
