---
title: Homepage
description: AWS Lambda MCP Cookbook - a Serverless MCP Server Blueprint
---
## **AWS AWS Lambda MCP Cookbook - a Serverless MCP Server Blueprint**

[<img alt="alt_text" src="./media/banner.png" width="400" />](https://www.ranthebuilder.cloud/)

## **The Problem**

Starting a production grade Serverless MCP can be overwhelming. You need to figure out many questions and challenges that have nothing to do with your business domain:

* How to deploy to the cloud? What IAC framework do you choose?
* How to write a SaaS-oriented CI/CD pipeline? What does it need to contain?
* How do you handle observability, logging, tracing, metrics?
* How do you write a production grade Lambda function?
* How do you handle testing?
* What makes an AWS Lambda handler resilient, traceable, and easy to maintain? How do you write such a code?

## **The Solution**

This project aims to reduce cognitive load and answer these questions for you by providing a skeleton Python Serverless service blueprint that implements best practices for AWS Lambda, Serverless CI/CD, and AWS CDK in one blueprint project.

The MCP server uses JSON RPC over HTTP (non streamable) via API Gateway's body payload parameter. See integration tests and see how the test event is generated.

![design](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/docs/media/design.png?raw=true)

### Serverless MCP Server

This project provides a working, open source based, pure AWS Lambda based Python MCP server implementation.

It contains a production grade implementation including DEPLOYMENT code with CDK and a CI/CD pipeline, testing, observability and more (see Features section).

NO Lambda adapter, no FastMCP - just pure Lambda as it was meant to be.

This project is a blueprint for new Serverless MCP servers.

It's based on [AWS sample for MCP](https://github.com/awslabs/mcp/tree/main/src/mcp-lambda-handler) combined with the [AWS Lambda Handler cookbook](https://ran-isenberg.github.io/aws-lambda-handler-cookbook/) template.

#### **Monitoring Design**

<img alt="monitoring" src="./media/monitoring_design.png" />

### **Features**

* PURE Lambda - not web adapter, no FastMCP required!
* Python Serverless MCP server with a recommended file structure.
* CDK infrastructure with infrastructure tests and security tests.
* Tests - unit, integration (tests for full MCP messages) and E2E with a real MCP client
* CI/CD pipelines based on Github actions that deploys to AWS with python linters, complexity checks and style formatters.
* CI/CD pipeline deploys to dev/staging and production environments with different gates between each environment
* Makefile for simple developer experience.
* The AWS Lambda handler embodies Serverless best practices and has all the bells and whistles for a proper production ready handler.
* AWS Lambda handler uses [AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda-python/).
* AWS Lambda handler 3 layer architecture: handler layer, logic layer and data access layer
* Session context storage in DynamoDB (does NOT send it to tools yet)
* API protected by WAF with four AWS managed rules in production deployment
* CloudWatch dashboards - High level and low level including CloudWatch alarms

The GitHub blueprint project can be found at [https://github.com/ran-isenberg/aws-lambda-mcp-cookbook](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook){:target="_blank" rel="noopener"}.

## **Serverless Best Practices**

The AWS Lambda handler will implement multiple best practice utilities.

Each utility is implemented when a new blog post is published about that utility.

The utilities cover multiple aspects of a production-ready service, including:

* [**Logging**](best_practices/logger.md)
* [**Observability: Monitoring and Tracing**](best_practices/tracer.md)
* [**Observability: Business KPI Metrics**](best_practices/metrics.md)
* [**Environment Variables**](best_practices/environment_variables.md)
* [**Hexagonal Architecture**](https://www.ranthebuilder.cloud/post/learn-how-to-write-aws-lambda-functions-with-architecture-layers)
* [**Input Validation**](best_practices/input_validation.md)
* [**Serverless Monitoring**](https://www.ranthebuilder.cloud/post/how-to-effortlessly-monitor-serverless-applications-with-cloudwatch-part-one)
* [**Learn How to Write AWS Lambda Functions with Three Architecture Layers**](https://www.ranthebuilder.cloud/post/learn-how-to-write-aws-lambda-functions-with-architecture-layers){:target="_blank" rel="noopener"}

While the code examples are written in Python, the principles are valid to any supported AWS Lambda handler programming language.

## Handler Examples

```python hl_lines="7 12 34" title="service/handlers/mcp.py"
--8<-- "docs/examples/best_practices/mcp/mcp.py"
```

Handler is found at service/handlers/mcp.py

MCP engine found at service/mcp_lambda_handler folder

## **License**

This library is licensed under the MIT License. See the [LICENSE](https://github.com/ran-isenberg/aws-lambda-mcp-cookbook/blob/main/LICENSE) file.
