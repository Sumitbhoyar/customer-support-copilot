"""
Environment-specific configuration settings.

Cost-optimized defaults for development/testing.
"""

from dataclasses import dataclass
import os


@dataclass
class Settings:
    """Application settings with cost-optimized defaults."""

    # Environment
    environment: str = "dev"
    aws_region: str = "eu-west-2"  # London (closest Bedrock region to Paris)

    # Bedrock Configuration
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"  # Cost-optimized
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # Knowledge Base Chunking
    chunking_max_tokens: int = 512
    chunking_overlap_percentage: int = 10

    # Database Configuration (Cost-optimized)
    db_instance_class: str = "db.t3.micro"  # Free tier eligible
    db_allocated_storage: int = 20  # Minimum GB

    # Lambda Configuration
    lambda_memory_mb: int = 512
    lambda_timeout_seconds: int = 30
    lambda_architecture: str = "ARM_64"  # 20% cheaper

    # Cache Configuration
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_max_size: int = 100

    @classmethod
    def from_environment(cls) -> "Settings":
        """Load settings from environment variables."""
        env = os.environ.get("ENVIRONMENT", "dev")

        # Production overrides
        if env == "prod":
            return cls(
                environment="prod",
                db_instance_class="db.t3.small",  # Upgrade for prod
                db_allocated_storage=50,
                lambda_memory_mb=1024,
                lambda_timeout_seconds=60,
            )

        return cls(environment=env)
