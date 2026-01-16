"""
Local orchestration service mirroring the Step Functions flow.

Used both for the HTTP fallback path and for unit/integration tests without
provisioning Step Functions.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List

from src.models.agent import (
    ClassificationResult,
    GenerationResult,
    OrchestrationResult,
    OrchestrationTrace,
    RetrievalResult,
    TicketInput,
)
from src.services.classification_service import ClassificationService
from src.services.response_service import ResponseService
from src.services.retrieval_service import RetrievalService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OrchestrationService:
    """Sequential orchestration that mirrors the state machine."""

    def __init__(self) -> None:
        self.classifier = ClassificationService()
        self.retriever = RetrievalService()
        self.responder = ResponseService()

    def run(self, ticket: TicketInput, correlation_id: str) -> OrchestrationResult:
        """Run classification -> retrieval -> generation with timing trace."""
        started_at = datetime.now(timezone.utc)

        c_start = time.perf_counter()
        classification: ClassificationResult = self.classifier.classify(ticket)
        c_latency = int((time.perf_counter() - c_start) * 1000)

        r_start = time.perf_counter()
        retrieval: RetrievalResult = self.retriever.build_context(ticket, classification)
        r_latency = int((time.perf_counter() - r_start) * 1000)

        g_start = time.perf_counter()
        generation: GenerationResult = self.responder.generate_response(
            ticket, classification, retrieval
        )
        g_latency = int((time.perf_counter() - g_start) * 1000)

        total_latency = c_latency + r_latency + g_latency

        trace = OrchestrationTrace(
            classification_latency_ms=c_latency,
            retrieval_latency_ms=r_latency,
            generation_latency_ms=g_latency,
            total_latency_ms=total_latency,
            state="completed" if not generation.guardrail_triggered else "completed_with_flags",
            started_at=started_at,
            correlation_id=correlation_id,
        )

        next_actions: List[str] = ["Send draft to agent queue for review"]
        if retrieval.aggregate_confidence < 0.6:
            next_actions.append("Escalate to L2 due to low retrieval confidence")

        return OrchestrationResult(
            classification=classification,
            context=retrieval,
            generation=generation,
            next_actions=next_actions,
            trace=trace,
        )
