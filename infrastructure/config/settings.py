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
    
    # Feature flag: set to False for first deploy to create collection/policies only
    # After collection is created, manually create the index, then set to True
    kb_enabled: bool = True
    aws_region: str = "eu-west-2"  # Default AWS region

    # Bedrock Configuration
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"  # Cost-optimized
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # Knowledge Base Chunking
    chunking_max_tokens: int = 512
    chunking_overlap_percentage: int = 10

    # Database Configuration (Cost-optimized)
    db_instance_class: str = "t3.micro"  # Free tier eligible
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
        kb_enabled = os.environ.get("KB_ENABLED", "true").lower() == "true"

        # Production overrides
        if env == "prod":
            return cls(
                environment="prod",
                kb_enabled=kb_enabled,
                db_instance_class="t3.small",  # Upgrade for prod
                db_allocated_storage=50,
                lambda_memory_mb=1024,
                lambda_timeout_seconds=60,
            )

        return cls(environment=env, kb_enabled=kb_enabled)
