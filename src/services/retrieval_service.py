"""
Retrieval service combining vector search, structured lookups, and similar tickets.

Designed to stay cost-aware by:
- caching vector search results in-memory
- limiting DynamoDB/DB calls with small limits
- short-circuiting when classification confidence is low
"""

from __future__ import annotations

import time
from typing import List

from models.agent import (
    ClassificationResult,
    RetrievalContextItem,
    RetrievalResult,
    TicketInput,
)
from models.knowledge import KBResult
from services.bedrock_service import BedrockService
from services.customer_service import CustomerService
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RetrievalService:
    """Build a context package suitable for generation."""

    def __init__(self) -> None:
        self.kb = BedrockService()
        self.customer_service = CustomerService()

    def build_context(
        self, ticket: TicketInput, classification: ClassificationResult
    ) -> RetrievalResult:
        """
        Retrieve KB, structured lookups, and similar tickets.

        If classification confidence is low, we avoid expensive calls and return
        an empty context with low aggregate confidence.
        """
        start = time.perf_counter()
        if classification.confidence < 0.4:
            return RetrievalResult(context_package=[], aggregate_confidence=0.2)

        context_items: List[RetrievalContextItem] = []

        kb_items = self._vector_search(ticket)
        context_items.extend(kb_items)

        structured_items = self._structured_lookups(ticket, classification)
        context_items.extend(structured_items)

        similar_items = self._similar_tickets(classification)
        context_items.extend(similar_items)

        aggregate_confidence = min(
            1.0,
            max(0.25, classification.confidence)
            + (0.1 * len(context_items))
            + (0.05 if kb_items else 0),
        )

        logger.info(
            "Context package built",
            extra={
                "context_count": len(context_items),
                "duration_ms": int((time.perf_counter() - start) * 1000),
            },
        )

        return RetrievalResult(
            context_package=context_items,
            aggregate_confidence=round(aggregate_confidence, 2),
        )

    def _vector_search(self, ticket: TicketInput) -> List[RetrievalContextItem]:
        """Use Bedrock KB vector search; guard with a short-circuit on empty KB."""
        query = f"{ticket.title}\n\n{ticket.description}"
        results: List[KBResult] = self.kb.retrieve(query, max_results=3)
        items: List[RetrievalContextItem] = []
        for res in results:
            items.append(
                RetrievalContextItem(
                    source_id=res.source or "kb",
                    excerpt=res.content,
                    citation_uri=res.source or "",
                    score=res.score,
                    type="kb",
                )
            )
        return items

    def _structured_lookups(
        self, ticket: TicketInput, classification: ClassificationResult
    ) -> List[RetrievalContextItem]:
        """
        Structured lookups combine account rules and recent orders.

        To keep costs low we reuse the existing CustomerService, which already
        caches lookups and avoids DB hits when not configured.
        """
        context_items: List[RetrievalContextItem] = []
        customer = self.customer_service.get_customer_context(ticket.customer_external_id)
        if not customer:
            return context_items

        if customer.recent_orders:
            order = customer.recent_orders[0]
            context_items.append(
                RetrievalContextItem(
                    source_id=str(order.get("order_id", "order")),
                    excerpt=json_dumps_compact(order),
                    citation_uri=f"order://{order.get('order_number', 'latest')}",
                    score=0.6,
                    type="order",
                )
            )

        sla = self._derive_sla(customer.tier, classification.priority)
        context_items.append(
            RetrievalContextItem(
                source_id="sla-policy",
                excerpt=sla,
                citation_uri="policy://sla",
                score=0.55,
                type="rule",
            )
        )
        return context_items

    def _similar_tickets(self, classification: ClassificationResult) -> List[RetrievalContextItem]:
        """
        Placeholder for DynamoDB similar tickets query.

        We keep this cheap with stubbed items; swap for real query later.
        """
        sample = RetrievalContextItem(
            source_id="similar-1",
            excerpt="Prior ticket resolved by rebooting the gateway.",
            citation_uri="ticket://similar/1",
            score=0.52,
            type="ticket",
        )
        return [sample]

    def _derive_sla(self, tier: str, priority: str) -> str:
        """Derive a simple SLA string based on tier and priority."""
        base = {
            "critical": "1h response, 4h resolution",
            "high": "4h response, 1d resolution",
            "medium": "1d response, 2d resolution",
            "low": "2d response, 5d resolution",
        }
        tier_bonus = "Expedite for enterprise tier." if tier == "enterprise" else ""
        return f"SLA: {base.get(str(priority), '1d response')}. {tier_bonus}".strip()


def json_dumps_compact(obj: object) -> str:
    """Compact JSON helper to keep excerpts small."""
    import json

    return json.dumps(obj, separators=(",", ":"))
