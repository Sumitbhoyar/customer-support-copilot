"""
End-to-end orchestration handler for POST /tickets/auto-orchestrate.

Prefers an AWS Step Functions state machine when configured (STATE_MACHINE_ARN);
otherwise falls back to an in-Lambda orchestration to keep dev/local flow simple.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Dict, Optional

import boto3

from models.agent import OrchestrationResult, TicketInput
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-loaded service and client to avoid import-time issues
_orchestrator: Optional["OrchestrationService"] = None
_sfn_client = None


def _get_orchestrator():
    """Lazy-load OrchestrationService."""
    global _orchestrator
    if _orchestrator is None:
        from services.orchestration_service import OrchestrationService
        _orchestrator = OrchestrationService()
    return _orchestrator


def _get_sfn_client():
    """Lazy-load Step Functions client."""
    global _sfn_client
    if _sfn_client is None:
        _sfn_client = boto3.client("stepfunctions")
    return _sfn_client


def lambda_handler(event, context) -> Dict:
    """Kick off the orchestration flow via Step Functions or local fallback."""
    correlation_id = str(uuid.uuid4())
    try:
        payload_body = event.get("body")
        if payload_body:
            payload = json.loads(payload_body)
        else:
            payload = event.get("ticket", event)
        ticket = TicketInput.model_validate(payload)

        state_machine_arn = os.environ.get("STATE_MACHINE_ARN")
        if state_machine_arn:
            execution_input = {
                "ticket": ticket.model_dump(mode="json"),
                "correlation_id": correlation_id,
            }
            execution = _get_sfn_client().start_sync_execution(
                stateMachineArn=state_machine_arn,
                name=f"exec-{correlation_id}",
                input=json.dumps(execution_input),
            )
            output = json.loads(execution.get("output", "{}"))
            result = OrchestrationResult.model_validate(output)
        else:
            # In dev/local we orchestrate synchronously inside this Lambda.
            result = _get_orchestrator().run(ticket=ticket, correlation_id=correlation_id)

        logger.info(
            "Orchestration complete",
            extra={
                "correlation_id": correlation_id,
                "trace_state": result.trace.state,
            },
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": result.model_dump_json(),
        }
    except Exception as exc:
        logger.exception("Orchestration failed", extra={"cid": correlation_id})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Auto-orchestrate failed",
                    "error": str(exc),
                    "correlation_id": correlation_id,
                }
            ),
        }
