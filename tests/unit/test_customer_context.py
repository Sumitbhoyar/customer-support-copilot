import json
from datetime import datetime, timezone

import pytest

from src.handlers import customer_context
from src.models.customer import CustomerContext


def _sample_customer_context() -> CustomerContext:
    return CustomerContext(
        customer_id="123",
        external_id="cust-ext-1",
        name="Jane Doe",
        email="jane@example.com",
        company="Example Co",
        tier="gold",
        lifetime_value=12500.0,
        total_orders=42,
        recent_orders=[],
        open_tickets=1,
        avg_sentiment=0.6,
        last_interaction=datetime.now(timezone.utc),
        is_high_value=True,
        churn_risk="medium",
    )


def test_customer_context_happy_path(monkeypatch):
    monkeypatch.setattr(
        customer_context.customer_service,
        "get_customer_context",
        lambda external_id: _sample_customer_context(),
    )
    event = {
        "pathParameters": {"id": "cust-ext-1"},
        "queryStringParameters": None,
    }

    resp = customer_context.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["email"] == "jane@example.com"
    assert body["churn_risk"] == "medium"


def test_customer_context_missing_id_returns_400():
    event = {"pathParameters": None, "queryStringParameters": None}
    resp = customer_context.lambda_handler(event, None)
    assert resp["statusCode"] == 400


def test_customer_context_not_found(monkeypatch):
    monkeypatch.setattr(
        customer_context.customer_service, "get_customer_context", lambda external_id: None
    )
    event = {
        "pathParameters": {"id": "unknown"},
        "queryStringParameters": None,
    }
    resp = customer_context.lambda_handler(event, None)
    assert resp["statusCode"] == 404
