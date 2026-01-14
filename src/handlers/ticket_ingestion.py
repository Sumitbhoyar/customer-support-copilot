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
from typing import Dict

from src.models.ticket import TicketRequest, TicketResponse
from src.services.customer_service import CustomerService
from src.services.bedrock_service import BedrockService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
customer_service = CustomerService()
bedrock_service = BedrockService(
    knowledge_base_id=None  # Set at runtime via env in handler below
)


def lambda_handler(event, context):
    """Handle POST /tickets."""
    start = time.perf_counter()
    correlation_id = str(uuid.uuid4())

    try:
        payload = json.loads(event.get("body") or "{}")
        ticket = TicketRequest.model_validate(payload)

        # Fetch customer context (uses cache + DB/DynamoDB).
        customer_context = customer_service.get_customer_context(
            ticket.customer_external_id
        )

        # Optionally get KB suggestions (guarded to keep costs down).
        suggestions = []
        if customer_context:
            query = f"{ticket.subject}\n\n{ticket.description}"
            suggestions = bedrock_service.retrieve(query, max_results=3)

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
