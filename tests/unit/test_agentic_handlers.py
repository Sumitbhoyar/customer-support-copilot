import json
from datetime import datetime, timezone

from src.handlers import classification, retrieval, response_generation, orchestration
from src.models.agent import (
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


def test_classification_handler_parses_ticket(monkeypatch):
    monkeypatch.setattr(classification.classifier, "classify", lambda t: _classification_result())
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


def test_retrieval_handler_accepts_direct_event(monkeypatch):
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
    monkeypatch.setattr(retrieval.retriever, "build_context", lambda ticket, classification: result)
    event = {
        "ticket": {
            "title": "Reset",
            "description": "router issue",
            "customer_external_id": "cust-1",
        },
        "classification": _classification_result().model_dump(),
    }
    resp = retrieval.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["context_package"][0]["source_id"] == "kb-1"


def test_response_generation_handler(monkeypatch):
    generation = GenerationResult(
        primary_draft=ResponseDraft(
            text="Draft 1", citations=["uri"], confidence=0.7, safety_flags=[]
        ),
        alternative_draft=None,
        suggested_next_steps=["Step"],
        guardrail_triggered=False,
    )
    monkeypatch.setattr(
        response_generation.responder,
        "generate_response",
        lambda ticket, classification, retrieval, use_sonnet=False: generation,
    )
    payload = {
        "ticket": {
            "title": "Reset",
            "description": "router issue",
            "customer_external_id": "cust-1",
        },
        "classification": _classification_result().model_dump(),
        "context": RetrievalResult(context_package=[], aggregate_confidence=0.5).model_dump(),
    }
    resp = response_generation.lambda_handler({"body": json.dumps(payload)}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["primary_draft"]["text"] == "Draft 1"


def test_orchestration_local_fallback(monkeypatch):
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
    monkeypatch.setenv("STATE_MACHINE_ARN", "")
    monkeypatch.setattr(orchestration.orchestrator, "run", lambda ticket, correlation_id: orchestration_result)
    payload = {
        "title": "Billing",
        "description": "Invoice wrong",
        "customer_external_id": "cust-1",
    }
    resp = orchestration.lambda_handler({"body": json.dumps(payload)}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["next_actions"] == ["Review"]
