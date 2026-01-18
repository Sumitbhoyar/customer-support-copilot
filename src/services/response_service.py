"""
Response generation service.

Produces 2 drafts with light guardrails and citations while defaulting to the
Haiku model for cost efficiency.
"""

from __future__ import annotations

import json
import os
import time
from typing import List

import boto3

from models.agent import (
    ClassificationResult,
    GenerationResult,
    ResponseDraft,
    RetrievalResult,
    SafetyFlag,
    TicketInput,
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ResponseService:
    """Generate drafts with basic guardrail logic."""

    def __init__(self) -> None:
        region = (
            os.environ.get("BEDROCK_REGION")
            or os.environ.get("AWS_REGION")
            or "eu-west-2"
        )
        self.model_id = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.sonnet_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def generate_response(
        self,
        ticket: TicketInput,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
        use_sonnet: bool = False,
    ) -> GenerationResult:
        """Call Bedrock, apply guardrails, and return drafts."""
        start = time.perf_counter()
        model = self.sonnet_model_id if use_sonnet else self.model_id
        prompt = self._build_prompt(ticket, classification, retrieval)

        flags: List[SafetyFlag] = []
        guardrail_triggered = False

        try:
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "messages": [
                            {"role": "user", "content": [{"type": "text", "text": prompt}]}
                        ],
                        "max_tokens": 600,
                        "temperature": 0.4,
                        "top_p": 0.9,
                    }
                ),
            )
            payload = json.loads(response["body"].read())
            text = payload["output"]["content"][0]["text"]
            primary, alternative = self._parse_drafts(text)
        except Exception as exc:
            logger.warning(
                "Model generation failed; providing safe fallback",
                extra={"error": str(exc)},
            )
            guardrail_triggered = True
            flags.append(SafetyFlag.LOW_CONTEXT_CONFIDENCE)
            primary = ResponseDraft(
                text="We have received your request and are reviewing it. "
                "A specialist will follow up shortly.",
                citations=[],
                confidence=0.4,
                safety_flags=[SafetyFlag.LOW_CONTEXT_CONFIDENCE],
            )
            alternative = None

        # Post-generation guardrails: ensure no promises beyond SLA.
        if "guarantee" in primary.text.lower():
            guardrail_triggered = True
            flags.append(SafetyFlag.OFF_BRAND)
            primary.safety_flags.append(SafetyFlag.OFF_BRAND)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Generation complete", extra={"duration_ms": duration_ms})

        return GenerationResult(
            primary_draft=primary,
            alternative_draft=alternative,
            suggested_next_steps=[
                "Verify if context coverage is sufficient.",
                "Escalate to L2 if customer is high-value and sentiment negative.",
            ],
            guardrail_triggered=guardrail_triggered,
        )

    def _build_prompt(
        self,
        ticket: TicketInput,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> str:
        """Construct a concise prompt with citations to minimize tokens."""
        context_lines = []
        for item in retrieval.context_package[:5]:
            context_lines.append(
                f"- [{item.type}] ({item.score:.2f}) {item.excerpt} (cite: {item.citation_uri})"
            )

        context_block = "\n".join(context_lines) or "No context available."
        return (
            "You are a concise, empathetic support assistant. "
            "Write 2 drafts separated by '\\n---\\n'. "
            "Each draft must cite sources using (cite: URI). "
            "Tone: professional, empathetic, solution-focused. "
            f"Classification: {classification.model_dump_json()}\n"
            f"Ticket: title={ticket.title}; description={ticket.description}\n"
            f"Context:\n{context_block}"
        )

    def _parse_drafts(self, text: str) -> tuple[ResponseDraft, ResponseDraft | None]:
        """
        Parse drafts from model output.

        We expect drafts separated by ---; if not present, treat entire text as one draft.
        """
        parts = [p.strip() for p in text.split("---") if p.strip()]
        primary_text = parts[0] if parts else text
        alternative_text = parts[1] if len(parts) > 1 else None

        primary = ResponseDraft(
            text=primary_text, citations=[], confidence=0.65, safety_flags=[]
        )
        alternative = (
            ResponseDraft(
                text=alternative_text, citations=[], confidence=0.55, safety_flags=[]
            )
            if alternative_text
            else None
        )
        return primary, alternative
