"""
Data layer construct: RDS PostgreSQL + DynamoDB interaction log table.
"""

from aws_cdk import (
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DataLayerConstruct(Construct):
    """Provision database resources."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        vpc: ec2.IVpc,
        db_instance_class: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # Secret for DB credentials (username auto-generated).
        self.db_secret = secretsmanager.Secret(
            self,
            "DbCredentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "app_user"}',
                generate_string_key="password",
                exclude_punctuation=True,
            ),
        )

        # RDS instance (single-AZ, storage-optimized for cost).
        self.db_instance = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                # Use a widely available Postgres engine version.
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            instance_type=ec2.InstanceType(db_instance_class),
            credentials=rds.Credentials.from_secret(self.db_secret),
            allocated_storage=20,
            storage_encrypted=True,
            backup_retention=Duration.days(3 if environment == "prod" else 0),
            multi_az=environment == "prod",
            publicly_accessible=False,
            deletion_protection=environment == "prod",
            removal_policy=RemovalPolicy.RETAIN if environment == "prod" else RemovalPolicy.DESTROY,
        )

        # DynamoDB table for interaction logs.
        self.interactions_table = dynamodb.Table(
            self,
            "CustomerInteractions",
            partition_key=dynamodb.Attribute(
                name="customer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=environment == "prod",
            removal_policy=RemovalPolicy.RETAIN if environment == "prod" else RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )
