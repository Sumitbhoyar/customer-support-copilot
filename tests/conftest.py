"""
Pytest configuration to ensure the project root is on sys.path.

This allows imports like `from src.handlers import health_check` to work
when running tests from any working directory on Windows/PowerShell.
"""

import os
import sys
from pathlib import Path

import boto3


def _ensure_repo_root_on_path() -> None:
    """Add repository root to sys.path if missing."""
    repo_root = Path(__file__).resolve().parents[1]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_root_on_path()

# Ensure boto3 has offline-friendly defaults so tests do not require AWS access.
os.environ.setdefault("AWS_REGION", "eu-west-2")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_SESSION_TOKEN", "test")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("BEDROCK_REGION", "eu-west-2")

# Create a default boto3 session so resources/clients do not error during import.
boto3.setup_default_session(region_name="eu-west-2")
