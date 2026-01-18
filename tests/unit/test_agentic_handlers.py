"""
Tests for the agentic workflow handlers.

These tests mock the underlying services to test handler logic only.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
SRC_PATH = Path(__file__).parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from models.agent import (
    Category,
    ClassificationResult,
    GenerationResult,
    OrchestrationResult,
    OrchestrationTrace,
    Priority,
    ResponseDraft,
    RetrievalContextItem,
    RetrievalResult,
    Sentiment,
)


def _classification_result() -> ClassificationResult:
    return ClassificationResult(
        category=Category.BILLING,
        priority=Priority.HIGH,
        department="Billing",
        sentiment=Sentiment.NEUTRAL,
        confidence=0.9,
        reasoning_snippet="Looks like billing.",
    )


def test_classification_handler_parses_ticket():
    """Test classification handler parses ticket and returns result."""
    from handlers import classification
    
    # Reset the lazy-loaded classifier
    classification._classifier = None
    
    mock_service = MagicMock()
    mock_service.classify.return_value = _classification_result()
    
    with patch.object(classification, '_get_classifier', return_value=mock_service):
        payload = {
            "title": "Billing issue",
            "description": "Invoice incorrect",
            "customer_external_id": "cust-1",
        }
        event = {"body": json.dumps(payload)}
        resp = classification.lambda_handler(event, None)
        
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["category"] == "billing"
    assert body["priority"] == "high"


def test_retrieval_handler_accepts_direct_event():
    """Test retrieval handler accepts direct event from Step Functions."""
    from handlers import retrieval
    
    # Reset the lazy-loaded retriever
    retrieval._retriever = None
    
    result = RetrievalResult(
        context_package=[
            RetrievalContextItem(
                source_id="kb-1",
                excerpt="Reset router",
                citation_uri="s3://kb/doc",
                score=0.9,
                type="kb",
            )
        ],
        aggregate_confidence=0.8,
    )
    
    mock_service = MagicMock()
    mock_service.build_context.return_value = result
    
    with patch.object(retrieval, '_get_retriever', return_value=mock_service):
        event = {
            "ticket": {
                "title": "Reset",
                "description": "router issue",
                "customer_external_id": "cust-1",
            },
            "classification": _classification_result().model_dump(mode="json"),
        }
        resp = retrieval.lambda_handler(event, None)
        
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["context_package"][0]["source_id"] == "kb-1"


def test_response_generation_handler():
    """Test response generation handler produces drafts."""
    from handlers import response_generation
    
    # Reset the lazy-loaded responder
    response_generation._responder = None
    
    generation = GenerationResult(
        primary_draft=ResponseDraft(
            text="Draft 1", citations=["uri"], confidence=0.7, safety_flags=[]
        ),
        alternative_draft=None,
        suggested_next_steps=["Step"],
        guardrail_triggered=False,
    )
    
    mock_service = MagicMock()
    mock_service.generate_response.return_value = generation
    
    with patch.object(response_generation, '_get_responder', return_value=mock_service):
        payload = {
            "ticket": {
                "title": "Reset",
                "description": "router issue",
                "customer_external_id": "cust-1",
            },
            "classification": _classification_result().model_dump(mode="json"),
            "context": RetrievalResult(context_package=[], aggregate_confidence=0.5).model_dump(mode="json"),
        }
        resp = response_generation.lambda_handler({"body": json.dumps(payload)}, None)
        
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["primary_draft"]["text"] == "Draft 1"


def test_orchestration_local_fallback(monkeypatch):
    """Test orchestration falls back to local execution without SFN ARN."""
    from handlers import orchestration
    
    # Reset the lazy-loaded orchestrator
    orchestration._orchestrator = None
    
    now = datetime.now(timezone.utc)
    orchestration_result = OrchestrationResult(
        classification=_classification_result(),
        context=RetrievalResult(context_package=[], aggregate_confidence=0.5),
        generation=GenerationResult(
            primary_draft=ResponseDraft(
                text="Hi", citations=[], confidence=0.6, safety_flags=[]
            ),
            alternative_draft=None,
            suggested_next_steps=[],
            guardrail_triggered=False,
        ),
        next_actions=["Review"],
        trace=OrchestrationTrace(
            classification_latency_ms=1,
            retrieval_latency_ms=1,
            generation_latency_ms=1,
            total_latency_ms=3,
            state="completed",
            started_at=now,
            correlation_id="cid",
        ),
    )
    
    # No SFN ARN means local fallback
    monkeypatch.setenv("STATE_MACHINE_ARN", "")
    
    mock_service = MagicMock()
    mock_service.run.return_value = orchestration_result
    
    with patch.object(orchestration, '_get_orchestrator', return_value=mock_service):
        payload = {
            "title": "Billing",
            "description": "Invoice wrong",
            "customer_external_id": "cust-1",
        }
        resp = orchestration.lambda_handler({"body": json.dumps(payload)}, None)
        
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["next_actions"] == ["Review"]
