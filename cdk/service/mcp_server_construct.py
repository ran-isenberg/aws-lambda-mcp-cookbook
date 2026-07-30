from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from boto3 import Session
from constructs import Construct

import cdk.service.constants as constants
from cdk.service.monitoring import Monitoring


# This implements a server-based API construct for the MCP server: an HTTP API GW in front of a
# Lambda running the ASGI app (MCP Python SDK) via the AWS Lambda Web Adapter extension.
class MCPServerConstruct(Construct):
    def __init__(self, scope: Construct, id_: str) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.region = Session().region_name
        self.db = self._build_db(id_prefix=f'{id_}db')
        self.log_group = self._build_log_group()
        self.lambda_role = self._build_lambda_role(self.db, self.log_group)
        self.common_layer = self._build_common_layer()
        self.mcp_func = self._add_post_lambda_integration(self.lambda_role, self.db, self.log_group)
        self.http_api = self._build_api_gw()
        self._create_mcp_integration(self.mcp_func, self.http_api)
        self.monitoring = Monitoring(self, id_, self.http_api, self.db, [self.mcp_func])

    def _build_db(self, id_prefix: str) -> dynamodb.TableV2:
        table_id = f'{id_prefix}{constants.TABLE_NAME}'
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=table_id,
            partition_key=dynamodb.Attribute(name='session_id', type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            removal_policy=RemovalPolicy.DESTROY,
        )
        CfnOutput(self, id=constants.MCP_TABLE_NAME_OUTPUT, value=table.table_name).override_logical_id(constants.MCP_TABLE_NAME_OUTPUT)
        return table

    def _create_mcp_integration(self, mcp: _lambda.Function, http_api: apigwv2.HttpApi) -> None:
        mcp_integration = HttpLambdaIntegration('McpIntegration', mcp)
        http_api.add_routes(path='/{proxy+}', methods=[apigwv2.HttpMethod.ANY], integration=mcp_integration)
        CfnOutput(self, constants.WEB_ADAPTER_MCP_API_URL, value=f'{http_api.api_endpoint}/mcp').override_logical_id(
            constants.WEB_ADAPTER_MCP_API_URL
        )

    def _build_api_gw(self) -> apigwv2.HttpApi:
        return apigwv2.HttpApi(self, 'McpHttpApi')

    def _build_log_group(self) -> logs.LogGroup:
        # An explicit log group replaces the Function's deprecated `log_retention` property. That
        # property provisions a LogRetention custom resource whose role carries the AWS managed
        # AWSLambdaBasicExecutionRole policy, which AwsSolutions-IAM4 flags.
        # The name is explicit (and stack-unique via id_) so the log policy below can be written
        # without CloudFormation tokens - see _build_lambda_role.
        return logs.LogGroup(
            self,
            'McpServerLogGroup',
            log_group_name=f'{constants.LAMBDA_LOG_GROUP_PREFIX}{self.id_}',
            retention=RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _build_lambda_role(self, db: dynamodb.TableV2, log_group: logs.LogGroup) -> iam.Role:
        # No AWS managed policies: AwsSolutions-IAM4 wants customer-managed permissions, so the
        # CloudWatch Logs grants that AWSLambdaBasicExecutionRole would provide are inlined here.
        # The resource is a literal ARN pattern rather than log_group.log_group_arn on purpose:
        # the latter renders as a CloudFormation token containing the generated logical id, which
        # would make the AwsSolutions-IAM5 acknowledgment in service_stack.py stack-name specific.
        return iam.Role(
            self,
            'mcpRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'dynamodb_db': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem'],
                            resources=[db.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                'cloudwatch_logs': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['logs:CreateLogStream', 'logs:PutLogEvents'],
                            resources=[constants.LAMBDA_LOG_GROUP_ARN_PATTERN],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
        )

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id_}{constants.LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_14],
            removal_policy=RemovalPolicy.DESTROY,
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )

    def _add_post_lambda_integration(
        self,
        role: iam.Role,
        db: dynamodb.TableV2,
        log_group: logs.LogGroup,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.MCP_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            architecture=_lambda.Architecture.ARM_64,
            handler='run.sh',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                # Available to the handler for application state. MCP itself no longer needs it:
                # the 2026-07-28 protocol is stateless and the server runs with stateless_http=True.
                'TABLE_NAME': db.table_name,
                'AWS_LAMBDA_EXEC_WRAPPER': '/opt/bootstrap',
                'PORT': '8000',
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[
                self.common_layer,
                PythonLayerVersion.from_layer_version_arn(
                    self,
                    f'{self.id_}web_adapter_layer',
                    f'arn:aws:lambda:{self.region}:{constants.WEB_ADAPTER_LAYER_ACCOUNT}:layer:{constants.WEB_ADAPTER_LAYER_NAME_ARM64}:{constants.WEB_ADAPTER_LAYER_NAME_VERSION}',
                ),
            ],
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.WARN,
        )

        return lambda_function
