---
title: Getting Started
description: AWS Lambda Cookbook Project Getting started
---
## **Prerequisites**

* **Docker** - install [Docker](https://www.docker.com/){target="_blank"}. Required for the Lambda layer packaging process.
* **[AWS CDK](cdk.md)** - Required for synth & deploying the AWS Cloudformation stack. Run CDK [Bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html) on your AWS account and region.
* Python 3.14
* [uv](https://docs.astral.sh/uv/){target="_blank"} - the project uses uv for dependency management; ``make dev`` installs it for you if it is missing.
* For Windows based machines, use the Makefile_windows version (rename to Makefile). Default Makefile is for Mac/Linux.

## Getting Started

You can start with a clean service out of this blueprint repository without using the 'Template' button on GitHub.

**That's it, you are ready to deploy the MCP server:**

```bash
cd {new repo folder}
make dev
make deploy
```

``make dev`` installs uv, syncs every dependency group into a local ``.venv``, installs the pre-commit hooks and runs ``npm ci`` for the pinned AWS CDK CLI.

You can also run 'make pr' will run all checks, synth, file formatters , unit tests, deploy to AWS and run integration and E2E tests.

## **Deploy CDK**

Create a cloudformation stack by running ``make deploy``.

## **Unit Tests**

Unit tests can be found under the ``tests/unit`` folder.

You can run the tests by using the following command: ``make unit``.

## **Integration Tests**

These tests drive the real MCP server in-process with an in-memory client, so they need no deployed stack and no AWS credentials.

They allow you to debug the MCP server in your IDE.

Integration tests can be found under the ``tests/integration`` folder.

You can run the tests by using the following command: ``make integration``.

## **E2E Tests**

Make sure you deploy the stack first.

E2E tests can be found under the ``tests/e2e`` folder.

These tests connect a real MCP client to the deployed API GW endpoint and exercise the tool, resource and prompt over the wire.

The tests are run automatically by: ``make e2e``.

## **Deleting the stack**

CDK destroy can be run with ``make destroy``.

## **Preparing Code for PR**

Run ``make pr``. This command will run all the required checks, pre commit hooks, linters, code formatters, import sorting and tests, so you can be sure GitHub's pipeline will pass.

The command auto fixes errors in the code for you.

If there's an error in the pre-commit stage, it gets auto fixed. However, are required to run ``make pr`` again so it continues to the next stages.

Be sure to commit all the changes that ``make pr`` does for you.

## **GitHub Pages Documentation**

``make docs`` can be run to start a local HTTP server with the project's documentation pages.

## **Building dev/lambda_requirements.txt**

### lambda_requirements.txt

CDK requires a requirements.txt in order to create a zip file with the Lambda layer dependencies. It is exported from ``pyproject.toml`` and ``uv.lock``.

``make deploy`` command will generate it automatically for you.

### dev_requirements.txt

This file is used during GitHub CI to install all the required Python libraries.

File contents are exported from the ``dev`` dependency group in ``pyproject.toml``.

``make deploy`` and ``make deps`` are commands generate it automatically.
