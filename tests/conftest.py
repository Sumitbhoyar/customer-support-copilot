"""
Pytest configuration to ensure paths are set up correctly for tests.

This allows imports like `from handlers import health_check` to work
when running tests, simulating the Lambda environment where code
is deployed from the src/ directory.
"""

import os
import sys
from pathlib import Path

import boto3


def _ensure_paths_on_sys_path() -> None:
    """Add repository root AND src/ to sys.path if missing.
    
    The src/ directory is added to simulate Lambda's import behavior,
    where Code.from_asset("src") makes src/ the root of the package.
    """
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    
    # Add repo root first (for imports like infrastructure.*)
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    
    # Add src/ for Lambda-style imports (from handlers import ...)
    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_paths_on_sys_path()

# Ensure boto3 has offline-friendly defaults so tests do not require AWS access.
os.environ.setdefault("AWS_REGION", "eu-west-2")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_SESSION_TOKEN", "test")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("BEDROCK_REGION", "eu-west-2")

# Lambda environment variables used by handlers
os.environ.setdefault("KNOWLEDGE_BASE_ID", "test-kb-id")
os.environ.setdefault("DB_SECRET_ARN", "arn:aws:secretsmanager:eu-west-2:123456789:secret:test")
os.environ.setdefault("INTERACTIONS_TABLE", "test-interactions-table")
os.environ.setdefault("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
os.environ.setdefault("DATA_SOURCE_ID", "test-data-source-id")

# Create a default boto3 session so resources/clients do not error during import.
boto3.setup_default_session(region_name="eu-west-2")
