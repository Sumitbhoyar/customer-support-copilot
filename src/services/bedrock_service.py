"""
Amazon Bedrock Knowledge Base Service.

Handles interactions with Bedrock KB for document retrieval and generation.
"""

from __future__ import annotations

import os
import hashlib
from typing import List, Optional

import boto3

from src.models.knowledge import KBResult
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BedrockService:
    """Service for Bedrock Knowledge Base operations."""

    def __init__(
        self,
        knowledge_base_id: Optional[str] = None,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: Optional[str] = None,
    ):
        self.knowledge_base_id = knowledge_base_id or os.environ.get("KNOWLEDGE_BASE_ID", "")
        self.model_id = model_id or os.environ.get("MODEL_ID", model_id)
        resolved_region = (
            region
            or os.environ.get("BEDROCK_REGION")
            or os.environ.get("AWS_REGION")
            or "eu-west-2"
        )
        self.bedrock_agent = boto3.client(
            "bedrock-agent-runtime",
            region_name=resolved_region,
        )
        self._cache = {}  # Simple in-memory cache

    def retrieve(
        self, query: str, max_results: int = 3, min_score: float = 0.5
    ) -> List[KBResult]:
        """Retrieve relevant documents from Knowledge Base with basic caching."""
        cache_key = self._get_cache_key(query, max_results)
        if cache_key in self._cache:
            logger.info("KB cache hit", extra={"query_hash": cache_key[:8]})
            return self._cache[cache_key]

        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                        "overrideSearchType": "HYBRID",
                    }
                },
            )

            results: List[KBResult] = []
            for item in response.get("retrievalResults", []):
                score = item.get("score", 0)
                if score >= min_score:
                    results.append(
                        KBResult(
                            content=item["content"]["text"],
                            score=score,
                            source=item.get("location", {})
                            .get("s3Location", {})
                            .get("uri", ""),
                            metadata=item.get("metadata", {}),
                        )
                    )

            self._cache[cache_key] = results
            logger.info(
                "KB retrieval complete",
                extra={"query_length": len(query), "results_count": len(results)},
            )
            return results
        except Exception as exc:
            logger.error("KB retrieval failed", extra={"error": str(exc)})
            return []

    def _get_cache_key(self, query: str, max_results: int) -> str:
        """Generate cache key from query parameters."""
        content = f"{query}:{max_results}"
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("KB cache cleared")
