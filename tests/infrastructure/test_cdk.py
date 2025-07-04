from aws_cdk import App
from aws_cdk.assertions import Template

from cdk.service.service_stack import ServiceStack


def test_synthesizes_properly():
    app = App()

    service_stack = ServiceStack(app, 'service-test', False)

    # Prepare the stack for assertions.
    template = Template.from_stack(service_stack)

    # verify that we have API GWs and DBs, verify not deleted by mistake prior to deployment
    template.resource_count_is('AWS::ApiGateway::RestApi', 1)
    template.resource_count_is('AWS::ApiGatewayV2::Api', 1)
    template.resource_count_is('AWS::DynamoDB::GlobalTable', 2)  # session db
