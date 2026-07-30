from aws_cdk import Acknowledgment, Stack, Tags, Validations
from cdk_nag import AwsSolutionsChecks
from constructs import Construct

from cdk.service.constants import LAMBDA_LOG_GROUP_ARN_PATTERN, OWNER_TAG, SERVICE_NAME, SERVICE_NAME_TAG
from cdk.service.mcp_server_construct import MCPServerConstruct
from cdk.service.utils import get_construct_name, get_username


class ServiceStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self._add_stack_tags()

        self.web_adapter_mcp_api = MCPServerConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='web_adapter'),
        )

        # add security check
        self._add_security_tests()

    def _add_stack_tags(self) -> None:
        # best practice to help identify resources in the console
        Tags.of(self).add(SERVICE_NAME_TAG, SERVICE_NAME)
        Tags.of(self).add(OWNER_TAG, get_username())

    def _add_security_tests(self) -> None:
        # cdk-nag v3 packs are validation plugins, not Aspects, and plugins may only be registered
        # on an App or Stage scope - hence the root construct (the App) rather than self.
        Validations.of(self.node.root).add_plugins(AwsSolutionsChecks(verbose=True))
        # v3 acknowledges findings through the CDK's native Validations API instead of
        # NagSuppressions. An acknowledgment covers the construct it is made on and its children,
        # so the IAM ones are scoped to the Lambda role rather than the whole stack - a wildcard
        # policy added anywhere else in the stack still fails the build.
        Validations.of(self.web_adapter_mcp_api.lambda_role).acknowledge(
            # Granular rules are acknowledged per finding: the bare rule id no longer matches.
            Acknowledgment(
                id=f'AwsSolutions-IAM5[Resource::{LAMBDA_LOG_GROUP_ARN_PATTERN}]',
                reason='log streams are created per invocation, so the stream name cannot be known up front.',
            ),
            Acknowledgment(
                id='AwsSolutions-IAM5[Resource::*]',
                reason='xray:PutTraceSegments and xray:PutTelemetryRecords have no resource-level permissions.',
            ),
        )
        # Non-granular rules are acknowledged with the pack-qualified id, on the API they concern.
        Validations.of(self.web_adapter_mcp_api.http_api).acknowledge(
            Acknowledgment(id='AwsSolutions::AwsSolutions-APIG1', reason='not mandatory in a sample blueprint'),
            Acknowledgment(id='AwsSolutions::AwsSolutions-APIG4', reason='authorization not mandatory in a sample blueprint'),
        )
