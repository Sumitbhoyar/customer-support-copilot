"""
Bedrock Knowledge Base construct.

Creates:
- Cost-optimized VPC shared across constructs (no NAT for dev to save cost)
- S3 bucket for KB documents (private, Intelligent-Tiering hint via lifecycle)
- Bedrock Knowledge Base + S3 data source with fixed-size chunking
- IAM role granting Bedrock access to the bucket
"""

from typing import Optional

from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_bedrock as bedrock,
)
from constructs import Construct


class KnowledgeBaseConstruct(Construct):
    """Provision the Bedrock KB foundation."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        embedding_model_id: str,
        chunking_max_tokens: int,
        chunking_overlap_percentage: int,
    ) -> None:
        super().__init__(scope, construct_id)

        # Shared VPC: no NAT in dev to avoid $30-40/mo; add endpoints instead.
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0 if environment != "prod" else 1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                    if environment == "prod"
                    else ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # Gateway endpoint for S3 so private subnets can reach S3 without NAT.
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # Documents bucket with lifecycle hint toward Intelligent-Tiering.
        self.documents_bucket = s3.Bucket(
            self,
            "KnowledgeDocsBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY if environment != "prod" else RemovalPolicy.RETAIN,
            auto_delete_objects=environment != "prod",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="IntelligentTieringHint",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(0),
                        )
                    ],
                )
            ],
        )

        # Role that Bedrock uses to access S3.
        self.kb_role = iam.Role(
            self,
            "BedrockKbRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        self.documents_bucket.grant_read(self.kb_role)

        # Knowledge Base definition (managed vector store).
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name=f"kb-{environment}",
            role_arn=self.kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=(
                        f"arn:aws:bedrock:{self.region}::foundation-model/{embedding_model_id}"
                    )
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS"
            ),
        )

        # Data source that ties the bucket to the KB with chunking config.
        self.data_source = bedrock.CfnDataSource(
            self,
            "KnowledgeBaseDataSource",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            name=f"kb-ds-{environment}",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.documents_bucket.bucket_arn,
                    inclusion_prefixes=[],
                    # Bedrock expects chunking configuration in data source.
                    knowledge_base_state="ENABLED",
                ),
            ),
            chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                chunking_strategy="FIXED_SIZE",
                fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                    max_tokens=chunking_max_tokens,
                    overlap_percentage=chunking_overlap_percentage,
                ),
            ),
        )

        # Ensure KB is created before the data source.
        self.data_source.add_dependency(self.knowledge_base)
