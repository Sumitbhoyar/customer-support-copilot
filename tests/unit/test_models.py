"""
Pydantic model validation tests.

Ensures all models validate correctly and reject invalid data.
No AWS connection required.

Run with: pytest tests/unit/test_models.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add src to path to simulate Lambda environment
SRC_PATH = Path(__file__).parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestTicketInput:
    """Test TicketInput model validation."""

    def test_valid_ticket_input(self):
        """Valid ticket input should pass validation."""
        from models.agent import TicketInput

        ticket = TicketInput(
            title="Cannot login",
            description="Getting error when trying to access account",
            customer_external_id="CUST001"
        )
        assert ticket.title == "Cannot login"
        assert ticket.customer_external_id == "CUST001"

    def test_ticket_input_requires_title(self):
        """TicketInput should require title."""
        from models.agent import TicketInput

        with pytest.raises(ValidationError) as exc_info:
            TicketInput(
                title="",  # Empty title
                description="Test description",
                customer_external_id="CUST001"
            )
        # Pydantic v2 raises validation error for empty string with validator
        assert exc_info.value.error_count() > 0

    def test_ticket_input_requires_description(self):
        """TicketInput should require description."""
        from models.agent import TicketInput

        with pytest.raises(ValidationError):
            TicketInput(
                title="Test title",
                description="",  # Empty description
                customer_external_id="CUST001"
            )

    def test_ticket_input_optional_fields(self):
        """TicketInput optional fields should have defaults."""
        from models.agent import TicketInput

        ticket = TicketInput(
            title="Test",
            description="Test description",
            customer_external_id="CUST001"
        )
        assert ticket.priority_hints is None
        assert ticket.channel == "email"  # Default value
        assert ticket.locale == "en-US"  # Default value


class TestClassificationResult:
    """Test ClassificationResult model."""

    def test_valid_classification_result(self):
        """Valid classification result should pass validation."""
        from models.agent import ClassificationResult, Category, Priority, Sentiment

        result = ClassificationResult(
            category=Category.TECHNICAL,
            priority=Priority.MEDIUM,
            department="Support",
            sentiment=Sentiment.NEUTRAL,
            confidence=0.85,
            reasoning_snippet="Technical issue with login"
        )
        assert result.category == Category.TECHNICAL
        assert result.priority == Priority.MEDIUM
        assert result.confidence == 0.85

    def test_classification_result_confidence_bounds(self):
        """Confidence should be between 0 and 1."""
        from models.agent import ClassificationResult, Category, Priority, Sentiment

        # Valid confidence
        result = ClassificationResult(
            category=Category.BILLING,
            priority=Priority.HIGH,
            department="Billing",
            sentiment=Sentiment.NEGATIVE,
            confidence=0.95,
            reasoning_snippet="Billing dispute"
        )
        assert result.confidence == 0.95


class TestRetrievalContextItem:
    """Test RetrievalContextItem model."""

    def test_valid_context_item(self):
        """Valid context item should pass validation."""
        from models.agent import RetrievalContextItem

        item = RetrievalContextItem(
            source_id="KB-001",
            excerpt="This is the relevant excerpt from knowledge base",
            citation_uri="s3://bucket/doc.pdf",
            score=0.92,
            type="kb"  # Correct field name
        )
        assert item.source_id == "KB-001"
        assert item.score == 0.92
        assert item.type == "kb"


class TestResponseDraft:
    """Test ResponseDraft model."""

    def test_valid_response_draft(self):
        """Valid response draft should pass validation."""
        from models.agent import ResponseDraft

        draft = ResponseDraft(
            text="Thank you for contacting us. We'll help resolve your issue.",
            citations=["KB-001", "KB-002"],
            confidence=0.88,
            safety_flags=[]
        )
        assert len(draft.citations) == 2
        assert draft.confidence == 0.88
        assert len(draft.safety_flags) == 0

    def test_response_draft_with_safety_flags(self):
        """Response draft with safety flags should pass validation."""
        from models.agent import ResponseDraft, SafetyFlag

        draft = ResponseDraft(
            text="I cannot provide that information.",
            citations=[],
            confidence=0.5,
            safety_flags=[SafetyFlag.LOW_CONTEXT_CONFIDENCE]
        )
        assert SafetyFlag.LOW_CONTEXT_CONFIDENCE in draft.safety_flags


class TestEnums:
    """Test enum values."""

    def test_category_enum_values(self):
        """Category enum should have expected values (lowercase)."""
        from models.agent import Category

        assert Category.TECHNICAL.value == "technical"
        assert Category.BILLING.value == "billing"
        assert Category.ACCOUNT.value == "account"
        assert Category.SHIPPING.value == "shipping"
        assert Category.OTHER.value == "other"

    def test_priority_enum_values(self):
        """Priority enum should have expected values (lowercase)."""
        from models.agent import Priority

        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"

    def test_sentiment_enum_values(self):
        """Sentiment enum should have expected values (lowercase)."""
        from models.agent import Sentiment

        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEUTRAL.value == "neutral"
        assert Sentiment.NEGATIVE.value == "negative"

    def test_safety_flag_enum_values(self):
        """SafetyFlag enum should have expected values."""
        from models.agent import SafetyFlag

        assert SafetyFlag.PII_DETECTED.value == "pii_detected"
        assert SafetyFlag.OFF_BRAND.value == "off_brand"
        assert SafetyFlag.UNSAFE_CONTENT.value == "unsafe_content"
        assert SafetyFlag.LOW_CONTEXT_CONFIDENCE.value == "low_context_confidence"


class TestCustomerContext:
    """Test CustomerContext model."""

    def test_valid_customer_context(self):
        """Valid customer context should pass validation."""
        from models.customer import CustomerContext

        context = CustomerContext(
            customer_id="CUST001",
            external_id="ext-001",
            name="John Doe",
            email="john@example.com",
            company="Acme Inc",
            tier="premium",
            lifetime_value=5000.00,
            total_orders=10,
            recent_orders=[],
            open_tickets=0,
            avg_sentiment=0.8,
            last_interaction=datetime.now(),
            is_high_value=True,
            churn_risk="low"
        )
        assert context.customer_id == "CUST001"
        assert context.tier == "premium"


class TestTicketRequest:
    """Test TicketRequest model."""

    def test_valid_ticket_request(self):
        """Valid ticket request should pass validation."""
        from models.ticket import TicketRequest

        request = TicketRequest(
            ticket_id="T-001",
            external_ticket_id="EXT-001",
            customer_external_id="CUST001",
            subject="Need help with billing",
            description="I was charged twice for my subscription",
            channel="email",
            priority="high",
            created_at=datetime.now()
        )
        assert request.subject == "Need help with billing"
        assert request.customer_external_id == "CUST001"
