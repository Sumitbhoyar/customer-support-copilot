"""Ticket models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from src.models.customer import CustomerContext
from src.models.knowledge import KBSuggestion


class TicketRequest(BaseModel):
    """Inbound ticket payload."""

    ticket_id: str
    external_ticket_id: str
    customer_external_id: str
    subject: str
    description: str
    channel: str
    priority: Optional[str] = "medium"
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime


class TicketResponse(BaseModel):
    """Response for ticket ingestion."""

    ticket_id: str
    status: str
    customer_context: Optional[CustomerContext] = None
    kb_suggestions: Optional[List[KBSuggestion]] = None
    processing_time_ms: int
    correlation_id: str
