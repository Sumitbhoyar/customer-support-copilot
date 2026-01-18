"""
Ticket ingestion handler.

Ingests tickets and returns a basic acknowledgement plus optional context.
For Phase 1 we keep it synchronous for simplicity/cost; SQS wiring can be
added later without changing the contract.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Optional

from models.ticket import TicketRequest, TicketResponse
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-loaded services to avoid import-time DB connections
_customer_service: Optional["CustomerService"] = None
_bedrock_service: Optional["BedrockService"] = None


def _get_customer_service():
    """Lazy-load CustomerService."""
    global _customer_service
    if _customer_service is None:
        from services.customer_service import CustomerService
        _customer_service = CustomerService()
    return _customer_service


def _get_bedrock_service():
    """Lazy-load BedrockService."""
    global _bedrock_service
    if _bedrock_service is None:
        from services.bedrock_service import BedrockService
        _bedrock_service = BedrockService(knowledge_base_id=None)
    return _bedrock_service


def lambda_handler(event, context):
    """Handle POST /tickets."""
    start = time.perf_counter()
    correlation_id = str(uuid.uuid4())

    try:
        payload = json.loads(event.get("body") or "{}")
        ticket = TicketRequest.model_validate(payload)

        # Fetch customer context (uses cache + DB/DynamoDB).
        customer_context = _get_customer_service().get_customer_context(
            ticket.customer_external_id
        )

        # Optionally get KB suggestions (guarded to keep costs down).
        suggestions = []
        if customer_context:
            query = f"{ticket.subject}\n\n{ticket.description}"
            suggestions = _get_bedrock_service().retrieve(query, max_results=3)

        response = TicketResponse(
            ticket_id=ticket.ticket_id,
            status="received",
            customer_context=customer_context,
            kb_suggestions=suggestions,
            processing_time_ms=int((time.perf_counter() - start) * 1000),
            correlation_id=correlation_id,
        )

        logger.info(
            "Ticket ingested",
            extra={"correlation_id": correlation_id, "ticket_id": ticket.ticket_id},
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": response.model_dump_json(),
        }

    except Exception as exc:  # broad to keep sample concise
        logger.exception("Ticket ingestion failed", extra={"correlation_id": correlation_id})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Invalid request",
                    "error": str(exc),
                    "correlation_id": correlation_id,
                }
            ),
        }


def feedback_handler(event, context):
    """Handle POST /tickets/{id}/feedback (stub for Phase 1)."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "accepted"}),
    }
