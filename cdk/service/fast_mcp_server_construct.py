from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from boto3 import Session
from constructs import Construct

import cdk.service.constants as constants
from cdk.service.monitoring import Monitoring


# this implements a server-based API construct for the MCP - use web-adapter extension to access the MCP and FastMCP
class FastMCPServerConstruct(Construct):
    def __init__(self, scope: Construct, id_: str) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.region = Session().region_name
        self.db = self._build_db(id_prefix=f'{id_}db')
        self.lambda_role = self._build_lambda_role(self.db)
        self.common_layer = self._build_common_layer()
        self.mcp_func = self._add_post_lambda_integration(self.lambda_role, self.db)
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
        CfnOutput(self, id=constants.FAST_MCP_TABLE_NAME_OUTPUT, value=table.table_name).override_logical_id(constants.FAST_MCP_TABLE_NAME_OUTPUT)
        return table

    def _create_mcp_integration(self, mcp: _lambda.Function, http_api: apigwv2.HttpApi) -> None:
        mcp_integration = HttpLambdaIntegration('McpIntegration', mcp)
        http_api.add_routes(path='/{proxy+}', methods=[apigwv2.HttpMethod.ANY], integration=mcp_integration)
        CfnOutput(self, constants.WEB_ADAPTER_MCP_API_URL, value=f'{http_api.api_endpoint}/mcp').override_logical_id(
            constants.WEB_ADAPTER_MCP_API_URL
        )

    def _build_api_gw(self) -> apigwv2.HttpApi:
        return apigwv2.HttpApi(self, 'McpHttpApi')

    def _build_lambda_role(self, db: dynamodb.TableV2) -> iam.Role:
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
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
        )

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f'{self.id_}{constants.LAMBDA_LAYER_NAME}',
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            removal_policy=RemovalPolicy.DESTROY,
            compatible_architectures=[_lambda.Architecture.X86_64],
        )

    def _add_post_lambda_integration(
        self,
        role: iam.Role,
        db: dynamodb.TableV2,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.MCP_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            architecture=_lambda.Architecture.X86_64,
            handler='run.sh',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                'TABLE_NAME': db.table_name,  # for mcp session store
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
                    f'arn:aws:lambda:{self.region}:{constants.WEB_ADAPTER_LAYER_ACCOUNT}:layer:{constants.WEB_ADAPTER_LAYER_NAME}:{constants.WEB_ADAPTER_LAYER_NAME_VERSION}',
                ),
            ],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.WARN,
        )

        return lambda_function
