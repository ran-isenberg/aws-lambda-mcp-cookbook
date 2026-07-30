---
title: Homepage
description: AWS Lambda MCP Cookbook - a Serverless MCP Server Blueprint
---
## **AWS Lambda MCP Cookbook - a Serverless MCP Server Blueprint**

[<img alt="Ran The Builder - Master Serverless and Platform Engineering" src="./media/banner.png" width="800" />](https://ranthebuilder.cloud/)

## **The Problem**

Starting a Serverless MCP can be overwhelming. You need to figure out many questions and challenges that have nothing to do with your business domain:

* How to deploy to the cloud? What IAC framework do you choose?
* How to write a SaaS-oriented CI/CD pipeline? What does it need to contain?
* How do you handle observability, logging, tracing, metrics?
* How do you write a well-structured Lambda function?
* How do you handle testing?
* What makes an AWS Lambda handler resilient, traceable, and easy to maintain? How do you write such a code?

## **The Solution**

This project aims to reduce cognitive load and answer these questions for you by providing an opinionated Python Serverless MCP server blueprint that implements best practices for AWS Lambda, MCP, Serverless CI/CD, and AWS CDK in one project.

This project is a blueprint for new Serverless MCP servers.

```mermaid
flowchart LR
    agents["MCP clients<br/>agents, IDEs"]
    waf["AWS WAF<br/>optional - see note"]
    gw["Amazon API Gateway<br/>HTTP API v2 · ANY proxy route"]

    subgraph fn["AWS Lambda · ARM64 · Python 3.14"]
        direction TB
        adapter["Lambda Web Adapter<br/>layer via AWS_LAMBDA_EXEC_WRAPPER"]
        uvi["uvicorn on :8000"]
        app["MCP server · mcp v2<br/>streamable_http_app at /mcp<br/>stateless_http · json_response"]
        adapter --> uvi --> app
    end

    ddb[("Amazon DynamoDB<br/>provisioned for app state")]
    cw["CloudWatch<br/>logs · metrics · dashboards · alarms"]
    xray["AWS X-Ray"]

    agents -->|"MCP over Streamable HTTP"| gw
    waf -.-> gw
    gw --> adapter
    app -.->|"unused by default"| ddb
    app --> cw
    app --> xray

    classDef optional stroke-dasharray: 5 5
    class waf,ddb optional
```

!!! note "AWS WAF is not attached today"
    WAF cannot front an API Gateway **HTTP** API (v2) - only a REST API.
    `WafToApiGatewayConstruct` in `cdk/service/waf_construct.py` is kept as a working reference:
    wire it up if you switch the edge to a REST API GW.

!!! note "DynamoDB is provisioned but unread"
    The `2026-07-28` protocol is stateless, so nothing touches the table out of the box -
    see [Session data and DynamoDB](#session-data-and-dynamodb).

### Serverless Lambda Web Adapter & the official MCP Python SDK

Based on [AWS Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) and the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp` v2).

Use an HTTP API GW and Lambda function. Can be used with a REST API GW with a custom domain too.

The server is an ordinary ASGI (Starlette) app served by uvicorn behind the Lambda Web Adapter, so it
upholds the official MCP protocol and has a native auth mechanism (OAuth).

### Protocol versions

The SDK's `streamable_http_app()` serves **both** MCP protocol eras from the same endpoint, routed
per request by the `MCP-Protocol-Version` header:

* `2026-07-28` - the current stateless spec: no `initialize` handshake, no `Mcp-Session-Id`.
* `2025-11-25` and earlier - the handshake era, for clients that have not migrated yet.

There is nothing to configure; both are always on.

### Session data and DynamoDB

The `2026-07-28` protocol is stateless: there is no `initialize` handshake and no `Mcp-Session-Id`, and
the server runs with `stateless_http=True`. Nothing is carried between requests for you.

That is a protocol change, not a restriction on your application. **The stack still provisions a
DynamoDB table and passes its name to the Lambda as `TABLE_NAME`, so you can use it to store session
or conversation state whenever you want it.** Nothing reads it out of the box - it is there for you
to build on.

The `lifespan` yields a shared context object, and the table is resolved from `TABLE_NAME` on first
use and reused thereafter - so the server still boots without any environment configured. A handler
reaches it through the injected `Context`. The approach the spec recommends is a server-minted handle: your tool writes state
to DynamoDB under a key it generates, returns that key to the client, and the client passes it back as
an ordinary tool argument on the next call.

```python
from mcp.server.mcpserver import Context


@mcp.tool()
def start_analysis(dataset: str, ctx: Context) -> str:
    """Begin an analysis and return a handle to resume it."""
    handle = str(uuid.uuid4())
    ctx.request_context.lifespan_context.table.put_item(Item={'session_id': handle, 'dataset': dataset})
    return handle


@mcp.tool()
def continue_analysis(handle: str, ctx: Context) -> str:
    """Continue an analysis previously started with start_analysis."""
    state = ctx.request_context.lifespan_context.table.get_item(Key={'session_id': handle})['Item']
    ...
```

The table's partition key is `session_id`, and the Lambda role already grants `GetItem`, `PutItem`,
`UpdateItem` and `DeleteItem` on it.

!!! warning
    A handle is a bearer token: anyone who has it can read that state. Bind it to the caller's
    identity (validate it against the authenticated principal) rather than trusting the handle alone.

#### **Monitoring Design**

```mermaid
flowchart LR
    subgraph sources["Monitored resources"]
        direction TB
        gw["HTTP API Gateway"]
        fn["Lambda function"]
        logs["CloudWatch Logs<br/>ERROR pattern widget"]
        ddb[("DynamoDB table")]
        kpi["Custom metric<br/>ValidMcpEvents"]
    end

    subgraph high["High level dashboard"]
        direction TB
        h1["API Gateway health"]
        h2["Daily MCP Requests"]
    end

    subgraph low["Low level dashboard"]
        direction TB
        l1["Lambda latency, errors,<br/>throttles, invocations"]
        l2["Error log widget"]
        l3["DynamoDB usage, latency,<br/>errors, throttles"]
    end

    alarms["CloudWatch alarms<br/>5xx error rate · p90 latency"]
    sns["SNS topic<br/>KMS encrypted"]

    gw --> h1
    kpi --> h2
    fn --> l1
    logs --> l2
    ddb --> l3

    h1 --> alarms
    l1 --> alarms
    l2 --> alarms
    alarms --> sns
```

### **Features**

* Python Serverless MCP server with a recommended file structure.
* Official MCP Python SDK v2 - supports the current `2026-07-28` spec and older clients alike.
* MCP Tools input validation: check argument types and values
* Tests - unit, integration (in-process MCP client against the real server) and E2E with a real MCP client
* CDK infrastructure with infrastructure tests and security tests.
* CI/CD pipelines based on Github actions that deploys to AWS with python linters, complexity checks and style formatters.
* CI/CD pipeline deploys to dev/staging and production environments with different gates between each environment
* Makefile for simple developer experience.
* The AWS Lambda handler embodies Serverless best practices and has all the bells and whistles for a well-structured handler.
* AWS Lambda handler uses [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda-python/).
* AWS Lambda handler 3 layer architecture: handler layer, logic layer and data access layer
* CloudWatch dashboards - High level and low level including CloudWatch alarms

The GitHub blueprint project can be found at [https://github.com/ran-isenberg/aws-lambda-mcp-cookbook](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook){:target="_blank" rel="noopener"}.

## **Serverless Best Practices**

The AWS Lambda handler will implement multiple best practice utilities.

Each utility is implemented when a new blog post is published about that utility.

The utilities cover multiple aspects of a well-structured service, including:

* [**Logging**](best_practices/logger.md)
* [**Observability: Monitoring and Tracing**](best_practices/tracer.md)
* [**Observability: Business KPI Metrics**](best_practices/metrics.md)
* [**Environment Variables**](best_practices/environment_variables.md)
* [**Hexagonal Architecture**](https://www.ranthebuilder.cloud/post/learn-how-to-write-aws-lambda-functions-with-architecture-layers)
* [**Input Validation**](best_practices/input_validation.md)
* [**Serverless Monitoring**](https://www.ranthebuilder.cloud/post/how-to-effortlessly-monitor-serverless-applications-with-cloudwatch-part-one)
* [**Learn How to Write AWS Lambda Functions with Three Architecture Layers**](https://www.ranthebuilder.cloud/post/learn-how-to-write-aws-lambda-functions-with-architecture-layers){:target="_blank" rel="noopener"}

While the code examples are written in Python, the principles are valid to any supported AWS Lambda handler programming language.

## Security

* Use the SDK's `auth` parameter on `MCPServer` for an OAuth implementation, or put an
  IAM/Cognito/Lambda authorizer in front of the API Gateway.
* DNS rebinding protection is switched off in `service/app.py`. That check exists to protect a
  server bound to a local port from browsers on the same machine; under the Lambda Web Adapter the
  app only listens on loopback inside the execution environment and API Gateway forwards its own
  Host header, so leaving it on would reject every request with `421 Misdirected Request`. API
  Gateway is where authn/authz belongs here.

!!! warning "WAF is not currently attached"
    AWS WAF cannot be attached to an API Gateway **HTTP** API (v2), only to a REST API. The
    `WafToApiGatewayConstruct` in `cdk/service/waf_construct.py` is kept as a reference
    implementation - wire it up if you front the Lambda with a REST API GW instead.

### Known Issues

* There might be security issues with this implementation, MCP is very new and has many issues.

## Handler Example

The MCP surface is split by capability kind, mirroring the business logic layout so each protocol
binding sits opposite the logic it exposes:

```text
service/
  app.py                     the ASGI app uvicorn serves - assembles everything below
  mcp_app/
    mcp_server.py            the MCPServer instance, its identity and instructions
    caching.py               cache hints advertised on catalog listings
    context.py               AppContext + lifespan (shared, per-process state)
    handlers/
      __init__.py            imports the modules below - this is what registers them
      tools.py               -> service/logic/math.py
      resources.py           -> service/logic/profiles.py
      prompts.py             -> service/logic/hld.py
```

A handler binds the protocol to a logic function and declares how clients may treat it:

```python title="service/mcp_app/handlers/tools.py"
--8<-- "service/mcp_app/handlers/tools.py"
```

The server object is built once, with its identity, lifespan and cache hints:

```python title="service/mcp_app/mcp_server.py"
--8<-- "service/mcp_app/mcp_server.py"
```

And the entrypoint pulls in the handlers and exposes the ASGI app:

```python title="service/app.py"
--8<-- "service/app.py"
```

!!! warning "Capabilities register on import"
    `@mcp.tool()`, `@mcp.resource()` and `@mcp.prompt()` register when their module is imported, so
    a new handler module must be imported in `service/mcp_app/handlers/__init__.py`. Forget it and
    the capability is silently missing from the catalog rather than raising - the listing tests in
    `tests/integration/test_mcp_server.py` are what catch that.

## **License**

This library is licensed under the MIT License. See the [LICENSE](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/LICENSE) file.
