"""Ticket processing service (placeholder for Phase 1)."""

from dataclasses import dataclass
from typing import Optional

from models.ticket import TicketRequest
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TicketProcessingResult:
    """Simple DTO describing ticket handling outcome."""

    status: str
    reason: Optional[str] = None


class TicketService:
    """Encapsulates ticket processing logic."""

    def process(self, ticket: TicketRequest) -> TicketProcessingResult:
        """
        Placeholder processing that can be expanded later.

        Keeping this method cheap avoids unnecessary compute while giving us a
        seam to add SQS/offline processing in Phase 2.
        """
        logger.info("Processing ticket", extra={"ticket_id": ticket.ticket_id})
        return TicketProcessingResult(status="received")
