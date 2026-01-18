"""
Context retrieval handler for POST /tickets/context.

Builds a context package using vector search + structured lookups + similar tickets.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Optional

from models.agent import ClassificationResult, RetrievalResult, TicketInput
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-loaded service to avoid import-time issues
_retriever: Optional["RetrievalService"] = None


def _get_retriever():
    """Lazy-load RetrievalService."""
    global _retriever
    if _retriever is None:
        from services.retrieval_service import RetrievalService
        _retriever = RetrievalService()
    return _retriever


def lambda_handler(event, context) -> Dict:
    """
    Validate payload and run retrieval.

    The handler accepts both the raw ticket and prior classification so we avoid
    re-classifying in the retrieval path.
    """
    correlation_id = str(uuid.uuid4())
    try:
        payload_body = event.get("body")
        if payload_body:
            payload = json.loads(payload_body)
        else:
            payload = event
        ticket = TicketInput.model_validate(payload.get("ticket", payload))
        classification = ClassificationResult.model_validate(
            payload.get("classification")
        )

        retrieval: RetrievalResult = _get_retriever().build_context(
            ticket=ticket, classification=classification
        )

        logger.info(
            "Context built",
            extra={
                "correlation_id": correlation_id,
                "context_items": len(retrieval.context_package),
            },
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": retrieval.model_dump_json(),
        }
    except Exception as exc:
        logger.exception("Context retrieval failed", extra={"cid": correlation_id})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Context retrieval failed",
                    "error": str(exc),
                    "correlation_id": correlation_id,
                }
            ),
        }
