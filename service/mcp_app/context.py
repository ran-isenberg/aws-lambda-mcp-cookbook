"""Shared per-process state and the lifespan that builds it."""

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import boto3
from aws_lambda_env_modeler import get_environment_variables
from mcp.server import MCPServer

from service.handlers.models.env_vars import McpHandlerEnvVars
from service.handlers.utils.observability import logger


class AppContext:
    """State shared by every request, built at most once per process.

    The DynamoDB table is resolved on first use rather than at startup. Doing it eagerly would
    make POWERTOOLS_SERVICE_NAME, LOG_LEVEL and TABLE_NAME mandatory just to boot the app - a
    missing one would fail the Lambda init instead of the request that actually needed the table,
    and `uvicorn service.mcp_server:app` would stop working for local development.
    """

    def __init__(self) -> None:
        self._table: Any = None
        self._lock = threading.Lock()

    @property
    def table(self) -> Any:
        """The DynamoDB table, built on first access and reused thereafter."""
        # Synchronous handlers run on anyio worker threads in v2, so two requests really can
        # race here on a cold start.
        with self._lock:
            if self._table is None:
                env_vars = get_environment_variables(model=McpHandlerEnvVars)
                logger.info('resolving dynamodb table', extra={'table_name': env_vars.TABLE_NAME})
                self._table = boto3.resource('dynamodb').Table(env_vars.TABLE_NAME)
        return self._table


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncGenerator[AppContext]:
    """Build shared state once, at startup.

    Under the v2 SDK the streamable HTTP lifespan is entered once when the session manager starts
    and the result is shared across every request - v1 re-entered it per request when
    stateless_http was on. Handlers reach the yielded object through
    ctx.request_context.lifespan_context.
    """
    yield AppContext()
