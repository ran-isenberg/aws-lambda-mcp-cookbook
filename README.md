# AWS Lambda MCP Cookbook (Python)

[![license](https://img.shields.io/github/license/ran-isenberg/aws-lambda-mcp-cookbook)](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/master/LICENSE)
![PythonSupport](https://img.shields.io/static/v1?label=python&message=3.13&color=blue?style=flat-square&logo=python)
[![codecov](https://codecov.io/github/ran-isenberg/aws-lambda-mcp-cookbook/graph/badge.svg?token=x9asxTtNQZ)](https://codecov.io/github/ran-isenberg/aws-lambda-mcp-cookbook)
![version](https://img.shields.io/github/v/release/ran-isenberg/aws-lambda-mcp-cookbook)
![github-star-badge](https://img.shields.io/github/stars/ran-isenberg/aws-lambda-mcp-cookbook.svg?style=social)
![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ran-isenberg/aws-lambda-mcp-cookbook/badge)
![issues](https://img.shields.io/github/issues/ran-isenberg/aws-lambda-mcp-cookbook)

<img src="https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/docs/media/banner.png?raw=true" width="400" alt="banner" />

This project provides a working, open source based, pure AWS Lambda based Python MCP server implementation.

It contains a production grade implementation including DEPLOYMENT code with CDK and a CI/CD pipeline, testing, observability and more (see Features section).

NO Lambda adapter, no FastMCP - just pure Lambda as it was meant to be.

This project is a blueprint for new Serverless MCP servers.

It's based on [AWS sample for MCP](https://github.com/awslabs/mcp/tree/main/src/mcp-lambda-handler) combined with the [AWS Lambda Handler cookbook]((https://ran-isenberg.github.io/aws-lambda-mcp-cookbook/)) template.

**[📜Documentation](https://ran-isenberg.github.io/aws-lambda-mcp-cookbook/)** | **[Blogs website](https://www.ranthebuilder.cloud)**
> **Contact details | mailto:ran.isenberg@ranthebuilder.cloud**

[![Twitter Follow](https://img.shields.io/twitter/follow/IsenbergRan?label=Follow&style=social)](https://twitter.com/RanBuilder)
[![Website](https://img.shields.io/badge/Website-www.ranthebuilder.cloud-blue)](https://www.ranthebuilder.cloud/)


## Getting Started

You can start with a clean service out of this blueprint repository without using the 'Template' button on GitHub.

**That's it, you are ready to deploy the MCP server (make sure Docker is running!):**

```bash
cd {new repo folder}
poetry env activate
poetry install
make deploy
```

Check out the official [Documentation](https://ran-isenberg.github.io/aws-lambda-mcp-cookbook/).

Make sure you have poetry v2 and above.

You can also run 'make pr' will run all checks, synth, file formatters , unit tests, deploy to AWS and run integration and E2E tests.

## **The Problem**

Starting a production grade Serverless MCP can be overwhelming. You need to figure out many questions and challenges that have nothing to do with your business domain:

* How to deploy to the cloud? What IAC framework do you choose?
* How to write a SaaS-oriented CI/CD pipeline? What does it need to contain?
* How do you handle observability, logging, tracing, metrics?
* How do you write a production grade Lambda function?
* How do you handle testing?
* What makes an AWS Lambda handler resilient, traceable, and easy to maintain? How do you write such a code?

## **The Solution**

This project aims to reduce cognitive load and answer these questions for you by providing a production grade Python Serverless MCP server blueprint that implements best practices for AWS Lambda, MCP, Serverless CI/CD, and AWS CDK in one project.

The MCP server uses JSON RPC over HTTP (non stream-able) via API Gateway's body payload parameter. See integration tests and see how the test event is generated.

```python
from aws_lambda_env_modeler import init_environment_variables
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.handlers.models.env_vars import McpHandlerEnvVars
from service.handlers.utils.authentication import authenticate
from service.handlers.utils.mcp import mcp
from service.handlers.utils.observability import logger, metrics, tracer
from service.logic.math import add_two_numbers


@mcp.tool()
def math(a: int, b: int) -> int:
    """Add two numbers together"""
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError('Invalid input: a and b must be integers')
    result = add_two_numbers(a, b)
    metrics.add_metric(name='ValidMcpEvents', unit=MetricUnit.Count, value=1)
    return result


@init_environment_variables(model=McpHandlerEnvVars)
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    authenticate(event, context)
    return mcp.handle_request(event, context)
```

### Serverless MCP Template


* The project deploys an API GW with an AWS Lambda integration under the path POST /mcp/ and stores session data in a DynamoDB table.

![design](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/docs/media/design.png?raw=true)
<br></br>

#### **Monitoring Design**

![monitoring_design](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/docs/media/monitoring_design.png?raw=true)
<br></br>

### **Features**

* PURE Lambda - not web adapter, no FastMCP required!
* Python Serverless MCP server with a recommended file structure.
* Tests - unit, integration (tests for full MCP messages) and E2E with a real MCP client
* CDK infrastructure with infrastructure tests and security tests.
* CI/CD pipelines based on Github actions that deploys to AWS with python linters, complexity checks and style formatters.
* CI/CD pipeline deploys to dev/staging and production environments with different gates between each environment
* Makefile for simple developer experience.
* The AWS Lambda handler embodies Serverless best practices and has all the bells and whistles for a proper production ready handler.
* AWS Lambda handler uses [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda-python/).
* AWS Lambda handler 3 layer architecture: handler layer, logic layer and data access layer
* Session context storage in DynamoDB (does NOT send it to tools yet)
* API protected by WAF with four AWS managed rules in production deployment
* CloudWatch dashboards - High level and low level including CloudWatch alarms

## CDK Deployment

The CDK code create an API GW with a path of /mcp which triggers the lambda on 'POST' requests.

The AWS Lambda handler uses a Lambda layer optimization which takes all the packages under the [packages] section in the Pipfile and downloads them in via a Docker instance.

This allows you to package any custom dependencies you might have, just add them to the Pipfile under the [packages] section.

## Serverless Best Practices

The AWS Lambda handler will implement multiple best practice utilities.

Each utility is implemented when a new blog post is published about that utility.

The utilities cover multiple aspect of a production-ready service, including:

* [Logging](https://www.ranthebuilder.cloud/post/aws-lambda-cookbook-elevate-your-handler-s-code-part-1-logging)
* [Observability: Monitoring and Tracing](https://www.ranthebuilder.cloud/post/aws-lambda-cookbook-elevate-your-handler-s-code-part-2-observability)
* [Observability: Business KPIs Metrics](https://www.ranthebuilder.cloud/post/aws-lambda-cookbook-elevate-your-handler-s-code-part-3-business-domain-observability)
* [Environment Variables](https://www.ranthebuilder.cloud/post/aws-lambda-cookbook-environment-variables)
* [Input Validation](https://www.ranthebuilder.cloud/post/aws-lambda-cookbook-elevate-your-handler-s-code-part-5-input-validation)
* [Hexagonal Architecture](https://www.ranthebuilder.cloud/post/learn-how-to-write-aws-lambda-functions-with-architecture-layers)
* [CDK Best practices](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook)
* [Serverless Monitoring](https://www.ranthebuilder.cloud/post/how-to-effortlessly-monitor-serverless-applications-with-cloudwatch-part-one)


## Security

- WAF connected in production accounts (requires having an environment variable during deployment called 'ENVIRONMENT' with a value of 'production')
- Auth/Authz function placeholder in the mcp.py handler function - see authentication.py
- It is recommended to either use IAM/Cognito/Lambda authorizer or use the authentication.py and implement identity provider token validation flow.

## Code Contributions

Code contributions are welcomed. Read this [guide.](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/CONTRIBUTING.md)

## Code of Conduct

Read our code of conduct [here.](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/CODE_OF_CONDUCT.md)

## Connect

- Email: ran.isenberg@ranthebuilder.cloud
- Blog: https://www.ranthebuilder.cloud
- Bluesky: [@ranthebuilder.cloud](https://bsky.app/profile/ranthebuilder.cloud)
- X:       [@RanBuilder](https://twitter.com/RanBuilder)
- LinkedIn: https://www.linkedin.com/in/ranbuilder/

## Credits

* [AWS Lambda Powertools (Python)](https://github.com/aws-powertools/powertools-lambda-python)
* [AWS sample for MCP](https://github.com/awslabs/mcp/tree/main/src/mcp-lambda-handler)
* [AWS Lambda Handler cookbook](https://ran-isenberg.github.io/aws-lambda-handler-cookbook/)

## License

This library is licensed under the MIT License. See the [LICENSE](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/LICENSE) file.
