from aws_cdk import Aspects, Stack, Tags
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from constructs import Construct

from cdk.service.constants import OWNER_TAG, SERVICE_NAME, SERVICE_NAME_TAG
from cdk.service.fast_mcp_server_construct import FastMCPServerConstruct
from cdk.service.mcp_construct import MCPApiConstruct
from cdk.service.utils import get_construct_name, get_username


class ServiceStack(Stack):
    def __init__(self, scope: Construct, id: str, is_production_env: bool, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self._add_stack_tags()

        self.pure_mcp_api = MCPApiConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='pure'),
            is_production_env=is_production_env,
        )

        self.web_adapter_mcp_api = FastMCPServerConstruct(
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
        Aspects.of(self).add(AwsSolutionsChecks(verbose=True))
        # Suppress a specific rule for this resource
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {'id': 'AwsSolutions-IAM4', 'reason': 'policy for cloudwatch logs.'},
                {'id': 'AwsSolutions-IAM5', 'reason': 'policy for cloudwatch logs.'},
                {'id': 'AwsSolutions-APIG2', 'reason': 'lambda does input validation'},
                {'id': 'AwsSolutions-APIG1', 'reason': 'not mandatory in a sample blueprint'},
                {'id': 'AwsSolutions-APIG3', 'reason': 'not mandatory in a sample blueprint'},
                {'id': 'AwsSolutions-APIG6', 'reason': 'not mandatory in a sample blueprint'},
                {'id': 'AwsSolutions-APIG4', 'reason': 'authorization not mandatory in a sample blueprint'},
                {'id': 'AwsSolutions-COG4', 'reason': 'not using cognito'},
                {'id': 'AwsSolutions-L1', 'reason': 'False positive'},
            ],
        )
