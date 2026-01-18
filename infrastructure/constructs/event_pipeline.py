"""
Event pipeline: S3 -> EventBridge -> Lambda to trigger KB sync.
"""

from aws_cdk import (
    Duration,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct


class EventPipelineConstruct(Construct):
    """Wire S3 uploads to a KB sync Lambda."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        documents_bucket: s3.IBucket,
        knowledge_base_id: str,
        data_source_id: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # Use AWS-managed Powertools layer (no Docker bundling needed)
        powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            "SyncPowertoolsLayer",
            f"arn:aws:lambda:{Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-arm64:7"
        )
        
        self.sync_lambda = _lambda.Function(
            self,
            "KbSyncHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handlers.kb_sync.lambda_handler",
            code=_lambda.Code.from_asset("src"),
            layers=[powertools_layer],
            timeout=Duration.seconds(60),
            memory_size=256,
            architecture=_lambda.Architecture.ARM_64,
            environment={
                "ENVIRONMENT": environment,
                "KNOWLEDGE_BASE_ID": knowledge_base_id,
                "DATA_SOURCE_ID": data_source_id,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        documents_bucket.grant_read(self.sync_lambda)

        # EventBridge rule for S3 Put/Delete events (covers all objects).
        events.Rule(
            self,
            "S3ToKbSyncRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created", "Object Deleted"],
                detail={"bucket": {"name": [documents_bucket.bucket_name]}},
            ),
            targets=[targets.LambdaFunction(self.sync_lambda)],
        )
