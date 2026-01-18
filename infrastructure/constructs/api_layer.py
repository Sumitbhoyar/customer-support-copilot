"""
API layer construct: shared Lambda + HTTP API routes.

A single Lambda keeps warm caches and reduces cold start costs.
Uses Docker bundling for dependencies (runs in CI/CD pipeline).
"""

from aws_cdk import (
    BundlingOptions,
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

        # AWS-managed Powertools layer (includes pydantic, boto3 extras)
        # Using x86_64 for CI/CD compatibility (GitHub runners are x86_64)
        powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            f"arn:aws:lambda:{scope.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86:7"
        )

        # Bundle Lambda code with dependencies using Docker (works in CI/CD)
        # Installs sqlalchemy, psycopg2-binary for database access
        bundled_code = _lambda.Code.from_asset(
            "src",
            bundling=BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                command=[
                    "bash", "-c",
                    "pip install -r requirements-lambda.txt -t /asset-output && "
                    "cp -r . /asset-output"
                ],
            ),
        )

        self.main_lambda = _lambda.Function(
            self,
            "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handlers.main.lambda_handler",
            code=bundled_code,
            layers=[powertools_layer],
            memory_size=lambda_memory_mb,
            timeout=Duration.seconds(lambda_timeout_seconds),
            architecture=_lambda.Architecture.X86_64,
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
            (apigw.HttpMethod.POST, "/tickets/classify"),
            (apigw.HttpMethod.POST, "/tickets/context"),
            (apigw.HttpMethod.POST, "/tickets/respond"),
            (apigw.HttpMethod.POST, "/tickets/auto-orchestrate"),
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
