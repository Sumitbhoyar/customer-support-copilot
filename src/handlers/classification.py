"""
Ticket classification handler for POST /tickets/classify.

The handler stays thin to keep cold-start costs down; the heavy lifting lives in
ClassificationService.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict

from src.models.agent import ClassificationResult, TicketInput
from src.services.classification_service import ClassificationService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
classifier = ClassificationService()


def lambda_handler(event, context) -> Dict:
    """
    Validate payload, call the classifier, and return structured output.

    We keep validation strict to avoid wasting Bedrock calls on bad inputs.
    """
    correlation_id = str(uuid.uuid4())
    try:
        payload_body = event.get("body")
        # Allow Step Functions to pass the ticket directly without API Gateway wrapper.
        if payload_body:
            payload = json.loads(payload_body)
        elif "ticket" in event:
            payload = event["ticket"]
        else:
            payload = event
        ticket = TicketInput.model_validate(payload)
        result: ClassificationResult = classifier.classify(ticket)

        logger.info(
            "Ticket classified",
            extra={"correlation_id": correlation_id, "category": result.category},
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": result.model_dump_json(),
        }
    except Exception as exc:
        logger.exception(
            "Classification failed", extra={"correlation_id": correlation_id}
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Classification failed",
                    "error": str(exc),
                    "correlation_id": correlation_id,
                }
            ),
        }
