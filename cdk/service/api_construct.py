from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_apigateway
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.service.constants as constants
from cdk.service.api_db_construct import ApiDbConstruct
from cdk.service.monitoring import CrudMonitoring
from cdk.service.waf_construct import WafToApiGatewayConstruct


class ApiConstruct(Construct):
    def __init__(self, scope: Construct, id_: str, is_production_env: bool) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.api_db = ApiDbConstruct(self, f'{id_}db')
        self.lambda_role = self._build_lambda_role(self.api_db.db)
        self.common_layer = self._build_common_layer()
        self.rest_api = self._build_api_gw()
        api_resource: aws_apigateway.Resource = self.rest_api.root.add_resource(constants.GW_RESOURCE)
        self.create_order_func = self._add_post_lambda_integration(api_resource, self.lambda_role, self.api_db.db)
        self.monitoring = CrudMonitoring(self, id_, self.rest_api, self.api_db.db, [self.create_order_func])
        if is_production_env:
            self.waf = WafToApiGatewayConstruct(self, f'{id_}waf', self.rest_api)

    def _build_api_gw(self) -> aws_apigateway.RestApi:
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            'mcp-api',
            rest_api_name='MCP Server',
            description='This service handles /mcp API requests.',
            deploy_options=aws_apigateway.StageOptions(throttling_rate_limit=2, throttling_burst_limit=10),
            cloud_watch_role=False,
        )

        CfnOutput(self, id=constants.APIGATEWAY, value=rest_api.url).override_logical_id(constants.APIGATEWAY)
        return rest_api

    def _build_lambda_role(self, db: dynamodb.TableV2) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
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
        )

    def _add_post_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.TableV2,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.MCP_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='service.handlers.mcp.lambda_handler',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                'TABLE_NAME': db.table_name,  # for mcp session store
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[self.common_layer],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
        )

        # POST /api/orders/
        api_resource.add_method(http_method='POST', integration=aws_apigateway.LambdaIntegration(handler=lambda_function))
        return lambda_function
