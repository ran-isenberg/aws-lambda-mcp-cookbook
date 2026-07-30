---
title: AWS CDK
description: AWS Lambda Cookbook CDK Project
---
## **Prerequisites**

- Follow this [getting started with CDK guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html){:target="_blank" rel="noopener"}
- Make sure your AWS account and machine can deploy an AWS Cloudformation stack and have all the tokens and configuration as described in the page above.
- CDK Best practices [blog](https://www.ranthebuilder.cloud/post/aws-cdk-best-practices-from-the-trenches){:target="_blank" rel="noopener"}
- Lambda layers best practices [blog](https://www.ranthebuilder.cloud/post/aws-lambda-layers-best-practice){:target="_blank" rel="noopener"}

## **CDK Deployment**

All CDK project files can be found under the CDK folder. See the [architecture diagram](index.md) on the homepage.

The CDK code creates an HTTP API GW that proxies every path to the Lambda, which serves MCP at /mcp.

The AWS Lambda handler uses a Lambda layer optimization: ``make build`` exports the runtime dependencies with ``uv export`` and CDK bundles them into a layer via Docker.

To add a new Lambda runtime dependency, add it to the ``dependencies`` list in ``pyproject.toml``.

To add a new dev dependency, add it to the ``dev`` dependency group in ``pyproject.toml``. Either way, run ``uv sync`` afterwards.

### **CDK Constants**

All AWS Lambda function configurations are saved as constants at the `cdk.service.constants.py` file and can easily be changed.

- Memory size
- Timeout in seconds
- Lambda dependencies build folder location
- Lambda Layer dependencies build folder location
- Various resources names
- Lambda function environment variables names and values

### **Deployed Resources**

- AWS Cloudformation stack: **cdk.service.service_stack.py** which is consisted of one construct
- Construct: **cdk.service.mcp_server_construct.py** which includes:
    - **Lambda Layer** - deployment optimization meant to be used with multiple handlers under the same API GW, sharing code logic and dependencies. You can read more about it [here.](https://www.ranthebuilder.cloud/post/aws-lambda-layers-best-practice){:target="_blank" rel="noopener"}
    - **Lambda Function** - The Lambda handler function itself. Handler code is taken from the service `folder`.
    - **Lambda Role** - The role of the Lambda function, with customer-managed permissions only.
    - **CloudWatch Log Group** - the function's log group, with an explicit retention policy.
    - **API GW with Lambda Integration** - an HTTP API GW that proxies every path to the Lambda function, which serves MCP at /mcp.
    - **AWS DynamoDB table** - available for application state. Nothing reads it out of the box, see [Session data and DynamoDB](index.md#session-data-and-dynamodb).

### **Infrastructure CDK & Security Tests**

Under tests there is an `infrastructure` folder for CDK infrastructure tests.

The first test, `test_cdk` uses CDK's testing framework which asserts that required resources exists so the application will not break anything upon deployment.

The security tests are based on `cdk_nag`. It checks your cloudformation output for security best practices. It can be found in the `service_stack.py` as part of the stack definition. It will fail the deployment when there is a security issue.

For more information click [here](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/check-aws-cdk-applications-or-cloudformation-templates-for-best-practices-by-using-cdk-nag-rule-packs.html){:target="_blank" rel="noopener"}.

### Deployed Resources

In the picture below you can see all the deployed resources ordered into domain groups. The image was created with the IDE plugin of AWS Application Composer.
