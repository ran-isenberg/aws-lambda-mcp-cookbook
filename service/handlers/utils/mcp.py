from aws_lambda_env_modeler import get_environment_variables

from service.handlers.models.env_vars import McpHandlerEnvVars
from service.mcp_lambda_handler.mcp_lambda_handler import MCPLambdaHandler
from service.mcp_lambda_handler.session import DynamoDBSessionStore

session_store = DynamoDBSessionStore(table_name_getter=lambda: get_environment_variables(model=McpHandlerEnvVars).TABLE_NAME)
mcp = MCPLambdaHandler(name='mcp-lambda-server', version='1.0.0', session_store=session_store)
