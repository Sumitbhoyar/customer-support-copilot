"""
Tests for customer context handler.
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


def test_customer_context_happy_path():
    """Test customer context returns 200 with valid customer."""
    from handlers import customer_context
    
    # Reset lazy-loaded service
    customer_context._customer_service = None
    
    mock_service = MagicMock()
    mock_service.get_customer_context.return_value = _sample_customer_context()
    
    with patch.object(customer_context, '_get_customer_service', return_value=mock_service):
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
    """Test missing customer ID returns 400."""
    from handlers import customer_context
    
    event = {"pathParameters": None, "queryStringParameters": None}
    resp = customer_context.lambda_handler(event, None)
    assert resp["statusCode"] == 400


def test_customer_context_not_found():
    """Test unknown customer returns 404."""
    from handlers import customer_context
    
    # Reset lazy-loaded service
    customer_context._customer_service = None
    
    mock_service = MagicMock()
    mock_service.get_customer_context.return_value = None
    
    with patch.object(customer_context, '_get_customer_service', return_value=mock_service):
        event = {
            "pathParameters": {"id": "unknown"},
            "queryStringParameters": None,
        }
        resp = customer_context.lambda_handler(event, None)
        
    assert resp["statusCode"] == 404
