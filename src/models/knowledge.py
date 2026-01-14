"""Knowledge base models."""

from typing import Optional
from pydantic import BaseModel


class KBResult(BaseModel):
    """Chunk returned from a KB retrieve call."""

    content: str
    score: float
    source: str
    metadata: dict


class KBSuggestion(KBResult):
    """Alias for clarity in ticket responses."""

    pass


class KBQuery(BaseModel):
    """Simple query wrapper."""

    query: str
    max_results: int = 3
    min_score: float = 0.5
