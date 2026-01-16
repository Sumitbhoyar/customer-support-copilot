"""
Response generation handler for POST /tickets/respond.

Produces multiple drafts with guardrail flags and citations.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict

from src.models.agent import (
    ClassificationResult,
    GenerationResult,
    RetrievalResult,
    TicketInput,
)
from src.services.response_service import ResponseService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
responder = ResponseService()


def lambda_handler(event, context) -> Dict:
    """
    Generate drafts from ticket + context + classification.

    Defaults to Haiku for cost; caller can request Sonnet via payload flag.
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
        retrieval = RetrievalResult.model_validate(payload.get("context"))
        use_sonnet = bool(payload.get("use_sonnet", False))

        generation: GenerationResult = responder.generate_response(
            ticket=ticket,
            classification=classification,
            retrieval=retrieval,
            use_sonnet=use_sonnet,
        )

        logger.info(
            "Response generated",
            extra={"correlation_id": correlation_id, "guardrail": generation.guardrail_triggered},
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": generation.model_dump_json(),
        }
    except Exception as exc:
        logger.exception("Response generation failed", extra={"cid": correlation_id})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Response generation failed",
                    "error": str(exc),
                    "correlation_id": correlation_id,
                }
            ),
        }
