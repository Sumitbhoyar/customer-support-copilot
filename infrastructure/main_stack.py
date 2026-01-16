"""
Main CDK Stack for AI Customer Support Platform.
"""

from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    aws_lambda as _lambda,
)
from constructs import Construct

from infrastructure.constructs.knowledge_base import KnowledgeBaseConstruct
from infrastructure.constructs.data_layer import DataLayerConstruct
from infrastructure.constructs.api_layer import ApiLayerConstruct
from infrastructure.constructs.event_pipeline import EventPipelineConstruct
from infrastructure.constructs.orchestration import OrchestrationConstruct
from infrastructure.config.settings import Settings


class AISupportStack(Stack):
    """Main stack wiring all constructs together."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        settings: Settings,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Global tags for cost/accounting.
        Tags.of(self).add("Project", "ai-customer-support")
        Tags.of(self).add("Environment", settings.environment)
        Tags.of(self).add("CostCenter", "support-automation")
        Tags.of(self).add("ManagedBy", "cdk")

        # 1) Knowledge Base + shared VPC.
        kb_construct = KnowledgeBaseConstruct(
            self,
            "KnowledgeBase",
            environment=settings.environment,
            embedding_model_id=settings.embedding_model_id,
            chunking_max_tokens=settings.chunking_max_tokens,
            chunking_overlap_percentage=settings.chunking_overlap_percentage,
        )

        # 2) Data layer.
        data_construct = DataLayerConstruct(
            self,
            "DataLayer",
            environment=settings.environment,
            vpc=kb_construct.vpc,
            db_instance_class=settings.db_instance_class,
        )

        # 3) API layer (single Lambda).
        api_construct = ApiLayerConstruct(
            self,
            "ApiLayer",
            environment=settings.environment,
            vpc=kb_construct.vpc,
            knowledge_base_id=kb_construct.knowledge_base.attr_knowledge_base_id,
            db_secret_arn=data_construct.db_secret.secret_arn,
            interactions_table_name=data_construct.interactions_table.table_name,
            model_id=settings.model_id,
            lambda_memory_mb=settings.lambda_memory_mb,
            lambda_timeout_seconds=settings.lambda_timeout_seconds,
        )

        # 3b) Orchestration (Step Functions + stage Lambdas).
        orchestration_construct = OrchestrationConstruct(
            self,
            "AgenticOrchestration",
            environment=settings.environment,
            lambda_code=_lambda.Code.from_asset("src"),
            shared_env={
                "ENVIRONMENT": settings.environment,
                "KNOWLEDGE_BASE_ID": kb_construct.knowledge_base.attr_knowledge_base_id,
                "DB_SECRET_ARN": data_construct.db_secret.secret_arn,
                "INTERACTIONS_TABLE": data_construct.interactions_table.table_name,
                "MODEL_ID": settings.model_id,
            },
            vpc=kb_construct.vpc,
        )
        orchestration_construct.state_machine.grant_start_execution(api_construct.main_lambda)
        api_construct.main_lambda.add_environment(
            "STATE_MACHINE_ARN", orchestration_construct.state_machine.state_machine_arn
        )

        # 4) Event pipeline to sync KB on document changes.
        event_construct = EventPipelineConstruct(
            self,
            "EventPipeline",
            environment=settings.environment,
            documents_bucket=kb_construct.documents_bucket,
            knowledge_base_id=kb_construct.knowledge_base.attr_knowledge_base_id,
            data_source_id=kb_construct.data_source.attr_data_source_id,
        )

        # Permissions for the API Lambda.
        kb_construct.documents_bucket.grant_read(api_construct.main_lambda)
        data_construct.db_secret.grant_read(api_construct.main_lambda)
        data_construct.interactions_table.grant_read_write_data(api_construct.main_lambda)
        # Permissions for orchestration stage Lambdas.
        kb_construct.documents_bucket.grant_read(orchestration_construct.retrieve_fn)
        data_construct.db_secret.grant_read(orchestration_construct.classify_fn)
        data_construct.db_secret.grant_read(orchestration_construct.retrieve_fn)
        data_construct.interactions_table.grant_read_write_data(orchestration_construct.retrieve_fn)
        data_construct.interactions_table.grant_read_write_data(orchestration_construct.respond_fn)

        # Outputs to quickly find resources.
        CfnOutput(self, "ApiEndpoint", value=api_construct.api.api_endpoint)
        CfnOutput(self, "KnowledgeBaseId", value=kb_construct.knowledge_base.attr_knowledge_base_id)
        CfnOutput(self, "DocumentsBucket", value=kb_construct.documents_bucket.bucket_name)
        CfnOutput(self, "InteractionsTable", value=data_construct.interactions_table.table_name)
        CfnOutput(
            self,
            "StateMachineArn",
            value=orchestration_construct.state_machine.state_machine_arn,
        )
