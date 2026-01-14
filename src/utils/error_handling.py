"""Custom exceptions and helpers for consistent error responses."""

from dataclasses import dataclass
from typing import Any, Dict


class AppError(Exception):
    """Base class for application errors."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(AppError):
    """Raised when a requested resource is missing."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=422)


def to_response(error: AppError) -> Dict[str, Any]:
    """Convert an AppError into a Lambda proxy integration response."""
    return {
        "statusCode": error.status_code,
        "headers": {"Content-Type": "application/json"},
        "body": f'{{"message": "{error}", "status": "error"}}',
    }
