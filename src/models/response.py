"""Common response wrapper."""

from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Generic API response."""

    message: str
    data: Optional[Any] = None
    correlation_id: Optional[str] = None
