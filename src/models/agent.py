"""Pydantic models for the Phase 2 agentic workflow."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TicketInput(BaseModel):
    """Normalized ticket payload used across classification/retrieval/generation."""

    title: str
    description: str
    customer_external_id: str
    channel: Optional[str] = "email"
    priority_hints: Optional[str] = None
    locale: Optional[str] = "en-US"
    metadata: dict = Field(default_factory=dict)

    @field_validator("title", "description")
    @classmethod
    def validate_required(cls, value: str) -> str:
        """Reject empty strings early to avoid wasting model calls."""
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("title and description must be provided")
        return cleaned


class Category(str, Enum):
    """Simple category placeholder until the taxonomy is finalized."""

    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    SHIPPING = "shipping"
    OTHER = "other"


class Priority(str, Enum):
    """Priority levels aligned with spec."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Sentiment(str, Enum):
    """Customer sentiment buckets."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ClassificationResult(BaseModel):
    """Structured classification output produced by Bedrock or heuristic fallback."""

    category: Category
    priority: Priority
    department: str
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    reasoning_snippet: str


class RetrievalContextItem(BaseModel):
    """Context chunk used for generation and citations."""

    source_id: str
    excerpt: str
    citation_uri: str
    score: float
    type: str = Field(description="kb|order|ticket|rule")


class RetrievalResult(BaseModel):
    """Aggregated retrieval result including confidence metric."""

    context_package: List[RetrievalContextItem] = Field(default_factory=list)
    aggregate_confidence: float = Field(ge=0, le=1)


class SafetyFlag(str, Enum):
    """Guardrail flags surfaced to clients for transparency."""

    PII_DETECTED = "pii_detected"
    OFF_BRAND = "off_brand"
    UNSAFE_CONTENT = "unsafe_content"
    LOW_CONTEXT_CONFIDENCE = "low_context_confidence"


class ResponseDraft(BaseModel):
    """Model output for a single draft."""

    text: str
    citations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    safety_flags: List[SafetyFlag] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """Complete generation output with optional fallback draft."""

    primary_draft: ResponseDraft
    alternative_draft: Optional[ResponseDraft] = None
    suggested_next_steps: List[str] = Field(default_factory=list)
    guardrail_triggered: bool = False


class OrchestrationTrace(BaseModel):
    """Lightweight trace for Step Functions output."""

    classification_latency_ms: int
    retrieval_latency_ms: int
    generation_latency_ms: int
    total_latency_ms: int
    state: str
    started_at: datetime
    correlation_id: str


class OrchestrationResult(BaseModel):
    """Bundle all stage outputs for the /auto-orchestrate endpoint."""

    classification: ClassificationResult
    context: RetrievalResult
    generation: GenerationResult
    next_actions: List[str] = Field(default_factory=list)
    trace: OrchestrationTrace
