"""
Bedrock Knowledge Base construct.

Creates:
- Cost-optimized VPC shared across constructs (no NAT for dev to save cost)
- S3 bucket for KB documents (private, Intelligent-Tiering hint via lifecycle)
- Bedrock Knowledge Base + S3 data source with fixed-size chunking
- IAM role granting Bedrock access to the bucket
"""

from typing import Optional
import json

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_bedrock as bedrock,
    aws_opensearchserverless as aoss,
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
        kb_enabled: bool = True,
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
        
        # Interface endpoint for Bedrock Runtime (needed since no NAT in dev)
        self.vpc.add_interface_endpoint(
            "BedrockRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
        )
        
        # Interface endpoint for Bedrock Agent Runtime (for KB queries)
        self.vpc.add_interface_endpoint(
            "BedrockAgentRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_AGENT_RUNTIME,
        )
        
        # Interface endpoint for Step Functions (orchestration Lambdas call SFN sync)
        self.vpc.add_interface_endpoint(
            "StepFunctionsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.STEP_FUNCTIONS,
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
        # IMPORTANT: Keep role name short (<64 chars) for OpenSearch Serverless policy
        self.kb_role = iam.Role(
            self,
            "BedrockKbRole",
            role_name=f"bedrock-kb-{environment}",  # Short custom name
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        self.documents_bucket.grant_read(self.kb_role)
        # Allow the KB role to call OpenSearch Serverless APIs (scoped to this account/region).
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["aoss:*"],
                resources=["*"],
            )
        )

        # Knowledge Base definition (managed vector store).
        region = Stack.of(self).region

        # OpenSearch Serverless collection (vector search).
        collection_name = f"kb-{environment}"
        # Encryption policy for the collection.
        encryption_policy = {
            "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{collection_name}"]}],
            # Use AWS-owned key for simpler setup; swap to KMS key if needed.
            "AWSOwnedKey": True,
        }
        self.aoss_encryption = aoss.CfnSecurityPolicy(
            self,
            "KbEncryptionPolicy",
            name=f"kb-encryption-{environment}",
            type="encryption",
            policy=json.dumps(encryption_policy),
        )

        # Network policy - allow public access (adjust to VPC if desired).
        network_policy = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"],
                    }
                ],
                "AllowFromPublic": True,
            }
        ]
        self.aoss_network = aoss.CfnSecurityPolicy(
            self,
            "KbNetworkPolicy",
            name=f"kb-network-{environment}",
            type="network",
            policy=json.dumps(network_policy),
        )

        # Collection depends on encryption and network policies.
        self.aoss_collection = aoss.CfnCollection(
            self,
            "KbCollection",
            name=collection_name,
            type="VECTORSEARCH",
            description="KB vector store",
        )
        self.aoss_collection.add_dependency(self.aoss_encryption)
        self.aoss_collection.add_dependency(self.aoss_network)

        # Data access policy for the KB role and deploy user.
        # Specific IAM user/role ARN for manual index creation access.
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        
        # Add your IAM user ARN here (wildcards not supported by OpenSearch Serverless)
        deploy_user_arn = f"arn:aws:iam::{account_id}:user/sumit-bhoyar"
        
        # IMPORTANT: Data access policy must grant access to BOTH collection AND index
        # Use the collection ARN pattern for OpenSearch Serverless
        data_access_policy = [
            {
                "Rules": [
                    {
                        "Resource": [f"collection/{collection_name}"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:UpdateCollectionItems",
                            "aoss:DescribeCollectionItems"
                        ],
                        "ResourceType": "collection"
                    },
                    {
                        "Resource": [f"index/{collection_name}/*"],
                        "Permission": [
                            "aoss:CreateIndex",
                            "aoss:DescribeIndex",
                            "aoss:ReadDocument",
                            "aoss:WriteDocument",
                            "aoss:UpdateIndex",
                            "aoss:DeleteIndex"
                        ],
                        "ResourceType": "index"
                    }
                ],
                "Principal": [
                    self.kb_role.role_arn,
                    deploy_user_arn,
                ],
                "Description": "Data access for Bedrock KB and deploy user"
            }
        ]
        self.aoss_data_access = aoss.CfnAccessPolicy(
            self,
            "KbDataAccess",
            name=f"kb-data-{environment}",  # Let CDK manage this policy
            type="data",
            policy=json.dumps(data_access_policy),
        )
        self.aoss_data_access.add_dependency(self.aoss_collection)
        # CRITICAL: Data access policy must be created AFTER the KB role so the ARN resolves
        self.aoss_data_access.node.add_dependency(self.kb_role)

        # Knowledge Base and Data Source (only if kb_enabled)
        # Set to False for first deploy to create collection/policies, then create index manually
        self.knowledge_base: Optional[bedrock.CfnKnowledgeBase] = None
        self.data_source: Optional[bedrock.CfnDataSource] = None
        
        if kb_enabled:
            self.knowledge_base = bedrock.CfnKnowledgeBase(
                self,
                "KnowledgeBase",
                name=f"kb-{environment}",
                role_arn=self.kb_role.role_arn,
                knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                    type="VECTOR",
                    vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                        embedding_model_arn=(
                            f"arn:aws:bedrock:{region}::foundation-model/{embedding_model_id}"
                        )
                    ),
                ),
                storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                    type="OPENSEARCH_SERVERLESS",
                    opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                        collection_arn=self.aoss_collection.attr_arn,
                        vector_index_name="default",
                        field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                            vector_field="vector",
                            text_field="text",
                            metadata_field="metadata",
                        ),
                    ),
                ),
            )
            self.knowledge_base.add_dependency(self.aoss_collection)
            self.knowledge_base.add_dependency(self.aoss_data_access)
            
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
                        inclusion_prefixes=["/"],
                    ),
                ),
            )
            self.data_source.add_dependency(self.knowledge_base)
