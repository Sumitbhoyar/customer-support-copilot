"""
Ticket classification service.

Uses Bedrock (Haiku by default) with a concise prompt and a cheap heuristic
fallback to avoid failed calls or budget surprises.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import boto3

from models.agent import (
    Category,
    ClassificationResult,
    Priority,
    Sentiment,
    TicketInput,
)
from utils.cache_service import LRUCache
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ClassificationService:
    """Encapsulates Bedrock classification with caching and fallback heuristics."""

    model_id: str = os.environ.get("MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    sonnet_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    cache_ttl_seconds: int = int(os.environ.get("CACHE_TTL_SECONDS", "300"))
    cache_max_size: int = int(os.environ.get("CACHE_MAX_SIZE", "128"))

    def __post_init__(self) -> None:
        region = (
            os.environ.get("BEDROCK_REGION")
            or os.environ.get("AWS_REGION")
            or "eu-west-2"
        )
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.cache = LRUCache(max_size=self.cache_max_size, ttl_seconds=self.cache_ttl_seconds)

    def classify(self, ticket: TicketInput, use_sonnet: bool = False) -> ClassificationResult:
        """Run classification with cache + heuristic fallback to save tokens."""
        cache_key = f"{ticket.title}:{ticket.description}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        start = time.perf_counter()
        try:
            model = self.sonnet_model_id if use_sonnet else self.model_id
            prompt = self._build_prompt(ticket)
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"type": "text", "text": prompt}],
                            }
                        ],
                        "max_tokens": 300,
                        "temperature": 0.2,
                        "top_p": 0.8,
                    }
                ),
            )
            payload = json.loads(response["body"].read())
            text = payload["output"]["content"][0]["text"]
            parsed = self._parse_response(text)
            self.cache.set(cache_key, parsed)
            return parsed
        except Exception as exc:
            logger.warning(
                "Model classification failed; falling back to heuristic",
                extra={"error": str(exc)},
            )
            fallback = self._heuristic(ticket)
            self.cache.set(cache_key, fallback)
            return fallback
        finally:
            logger.info(
                "Classification latency captured",
                extra={"duration_ms": int((time.perf_counter() - start) * 1000)},
            )

    def _build_prompt(self, ticket: TicketInput) -> str:
        """Small prompt to minimize tokens while extracting needed fields."""
        return (
            "You are a support triage assistant. "
            "Return JSON with fields: category (billing|technical|account|shipping|other), "
            "priority (critical|high|medium|low), department, sentiment (positive|neutral|negative), "
            "confidence (0-1), reasoning_snippet. "
            f"Title: {ticket.title}\nDescription: {ticket.description}\n"
            f"Channel: {ticket.channel}\nPriority hints: {ticket.priority_hints or 'none'}"
        )

    def _parse_response(self, text: str) -> ClassificationResult:
        """Best-effort JSON extraction to keep the response structured."""
        try:
            parsed = json.loads(text)
            return ClassificationResult.model_validate(parsed)
        except Exception:
            # If the model returned non-JSON, fall back to heuristic.
            raise ValueError("Model returned unparseable response")

    def _heuristic(self, ticket: TicketInput) -> ClassificationResult:
        """Fallback classification that avoids model spend when necessary."""
        lower_text = f"{ticket.title} {ticket.description}".lower()

        if "billing" in lower_text or "invoice" in lower_text:
            category = Category.BILLING
            department = "Billing"
        elif "password" in lower_text or "login" in lower_text:
            category = Category.ACCOUNT
            department = "Account"
        elif "shipping" in lower_text or "delivery" in lower_text:
            category = Category.SHIPPING
            department = "Logistics"
        elif "error" in lower_text or "fail" in lower_text:
            category = Category.TECHNICAL
            department = "Support"
        else:
            category = Category.OTHER
            department = "Support"

        priority = Priority.MEDIUM
        if "outage" in lower_text or "down" in lower_text:
            priority = Priority.CRITICAL
        elif "urgent" in lower_text or "asap" in lower_text:
            priority = Priority.HIGH

        sentiment = (
            Sentiment.NEGATIVE
            if "angry" in lower_text or "frustrated" in lower_text
            else Sentiment.NEUTRAL
        )

        return ClassificationResult(
            category=category,
            priority=priority,
            department=department,
            sentiment=sentiment,
            confidence=0.55,
            reasoning_snippet="Heuristic fallback based on keywords.",
        )
