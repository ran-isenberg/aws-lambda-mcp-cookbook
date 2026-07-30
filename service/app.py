"""The ASGI app. `run.sh` serves this module's `app` with uvicorn behind the Lambda Web Adapter.

Importing this module assembles the whole server: `mcp` comes from `service.mcp_app.mcp_server`
and importing `handlers` runs the decorators that register every capability on it. The dependency
runs one way - app -> handlers -> mcp_server - so nothing here needs a deferred import.
"""

from mcp.server.transport_security import TransportSecuritySettings

from service.mcp_app import handlers  # noqa: F401  - imported for its registration side effect
from service.mcp_app.mcp_server import mcp

# DNS rebinding protection guards a server that binds a local port against browsers on the same
# machine. Under the Lambda Web Adapter the app only ever listens on loopback inside the execution
# environment, and the public edge is API Gateway - which forwards its own Host header. Leaving the
# default on would reject every request with 421 Misdirected Request, so it is turned off here and
# the edge is where authn/authz belongs.
app = mcp.streamable_http_app(
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
