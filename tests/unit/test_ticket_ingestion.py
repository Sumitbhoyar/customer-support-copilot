"""
Tests for ticket ingestion handler.
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

from models.customer import CustomerContext
from models.knowledge import KBSuggestion


def _sample_customer_context() -> CustomerContext:
    """Build a realistic customer context object."""
    return CustomerContext(
        customer_id="123",
        external_id="cust-ext-1",
        name="Jane Doe",
        email="jane@example.com",
        company="Example Co",
        tier="gold",
        lifetime_value=12500.0,
        total_orders=42,
        recent_orders=[{"order_id": "o-1", "order_number": "1001", "total_amount": 199.0}],
        open_tickets=1,
        avg_sentiment=0.6,
        last_interaction=datetime.now(timezone.utc),
        is_high_value=True,
        churn_risk="medium",
    )


def test_ticket_ingestion_happy_path():
    """Ticket ingestion returns context and suggestions."""
    from handlers import ticket_ingestion
    
    # Reset lazy-loaded services
    ticket_ingestion._customer_service = None
    ticket_ingestion._bedrock_service = None
    
    # Mock customer service
    mock_customer_service = MagicMock()
    mock_customer_service.get_customer_context.return_value = _sample_customer_context()
    
    # Mock bedrock service
    suggestion = KBSuggestion(
        content="Reset the router and retry.",
        score=0.87,
        source="s3://kb/docs/troubleshooting.md",
        metadata={"section": "network"},
    )
    mock_bedrock_service = MagicMock()
    mock_bedrock_service.retrieve.return_value = [suggestion]
    
    with patch.object(ticket_ingestion, '_get_customer_service', return_value=mock_customer_service):
        with patch.object(ticket_ingestion, '_get_bedrock_service', return_value=mock_bedrock_service):
            payload = {
                "ticket_id": "t-1",
                "external_ticket_id": "ext-1",
                "customer_external_id": "cust-ext-1",
                "subject": "Network issue",
                "description": "Cannot connect to VPN",
                "channel": "email",
                "priority": "high",
                "metadata": {"region": "EU"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            event = {"body": json.dumps(payload)}
            resp = ticket_ingestion.lambda_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ticket_id"] == "t-1"
    assert body["status"] == "received"
    assert body["customer_context"]["email"] == "jane@example.com"
    assert body["kb_suggestions"][0]["content"] == "Reset the router and retry."
    assert "correlation_id" in body
    assert body["processing_time_ms"] >= 0


def test_ticket_ingestion_bad_payload_returns_400():
    """Invalid payload should produce a 400 with an error message."""
    from handlers import ticket_ingestion
    
    event = {"body": json.dumps({"ticket_id": "missing_fields_only"})}
    resp = ticket_ingestion.lambda_handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["message"] == "Invalid request"
