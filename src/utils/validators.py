"""Lightweight validation helpers (placeholder for future expansion)."""

from typing import Any


def ensure_present(value: Any, field: str) -> None:
    """Raise ValueError if value is falsy."""
    if value in (None, "", []):
        raise ValueError(f"{field} is required")
