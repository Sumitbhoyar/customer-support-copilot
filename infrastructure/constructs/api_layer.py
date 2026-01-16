"""
API layer construct: shared Lambda + HTTP API routes.

A single Lambda keeps warm caches and reduces cold start costs.
"""

from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_logs as logs,
)
from constructs import Construct


class ApiLayerConstruct(Construct):
    """Expose ticketing endpoints via HTTP API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        vpc: ec2.IVpc,
        knowledge_base_id: str,
        db_secret_arn: str,
        interactions_table_name: str,
        model_id: str,
        lambda_memory_mb: int = 512,
        lambda_timeout_seconds: int = 30,
    ) -> None:
        super().__init__(scope, construct_id)

        # Main Lambda that routes based on HTTP path/method.
        self.main_lambda = _lambda.Function(
            self,
            "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handlers.main.lambda_handler",
            code=_lambda.Code.from_asset("src"),
            memory_size=lambda_memory_mb,
            timeout=Duration.seconds(lambda_timeout_seconds),
            architecture=_lambda.Architecture.ARM_64,
            vpc=vpc,
            environment={
                "ENVIRONMENT": environment,
                "KNOWLEDGE_BASE_ID": knowledge_base_id,
                "DB_SECRET_ARN": db_secret_arn,
                "INTERACTIONS_TABLE": interactions_table_name,
                "MODEL_ID": model_id,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # HTTP API with minimal latency and low cost.
        self.api = apigw.HttpApi(
            self,
            "HttpApi",
            api_name=f"ai-support-api-{environment}",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
            ),
        )

        integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration", self.main_lambda
        )

        # Register routes from the spec.
        route_defs = [
            (apigw.HttpMethod.POST, "/tickets"),
            (apigw.HttpMethod.GET, "/tickets/{id}/context"),
            (apigw.HttpMethod.POST, "/tickets/{id}/feedback"),
            (apigw.HttpMethod.GET, "/health"),
            (apigw.HttpMethod.POST, "/kb/sync"),
        ]

        for method, path in route_defs:
            route_key = apigw.HttpRouteKey.with_(method=method, path=path)
            self.api.add_routes(
                path=path,
                methods=[method],
                integration=integration,
            )
