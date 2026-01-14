"""
Pytest configuration to ensure the project root is on sys.path.

This allows imports like `from src.handlers import health_check` to work
when running tests from any working directory on Windows/PowerShell.
"""

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    """Add repository root to sys.path if missing."""
    repo_root = Path(__file__).resolve().parents[1]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_root_on_path()
