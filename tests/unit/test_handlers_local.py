"""
Local handler tests using mocks.

These tests validate handler logic without connecting to AWS.
AWS services are mocked using unittest.mock.

Run with: pytest tests/unit/test_handlers_local.py -v
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path to simulate Lambda environment
SRC_PATH = Path(__file__).parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestHealthCheckHandler:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self):
        """Health check should return 200 with status ok."""
        from handlers.health_check import lambda_handler

        result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "ok"
        assert "timestamp" in body

    def test_health_check_includes_environment(self):
        """Health check should include environment from env var."""
        from handlers.health_check import lambda_handler

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            result = lambda_handler({}, None)
            body = json.loads(result["body"])
            # Environment is read at handler time
            assert "environment" in body


class TestMainRouter:
    """Test the main Lambda router."""

    def test_router_returns_404_for_unknown_route(self):
        """Unknown routes should return 404."""
        from handlers.main import lambda_handler

        event = {
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/unknown/path"
                }
            }
        }
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Route not found" in body["message"]

    def test_router_routes_health_check(self):
        """GET /health should route to health_check handler."""
        from handlers.main import lambda_handler

        event = {
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/health"
                }
            }
        }
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "ok"


class TestClassificationHandler:
    """Test the classification handler."""

    def test_classification_validates_input(self):
        """Classification should reject invalid input."""
        from handlers.classification import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({"title": ""})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "correlation_id" in body

    def test_classification_with_valid_input(self):
        """Classification should process valid input with mocked service."""
        from handlers import classification
        from handlers.classification import lambda_handler
        from models.agent import ClassificationResult, Category, Priority, Sentiment
        
        # Reset lazy-loaded classifier
        classification._classifier = None
        
        mock_result = ClassificationResult(
            category=Category.TECHNICAL,
            priority=Priority.MEDIUM,
            department="Support",
            sentiment=Sentiment.NEUTRAL,
            confidence=0.85,
            reasoning_snippet="Technical issue"
        )
        
        mock_service = MagicMock()
        mock_service.classify.return_value = mock_result

        with patch.object(classification, '_get_classifier', return_value=mock_service):
            event = {
                "body": json.dumps({
                    "title": "Cannot login to account",
                    "description": "Getting error when trying to access my account",
                    "customer_external_id": "CUST001"
                })
            }
            result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["category"] == "technical"


class TestRetrievalHandler:
    """Test the retrieval handler."""

    def test_retrieval_validates_input(self):
        """Retrieval should reject invalid input."""
        from handlers.retrieval import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestResponseGenerationHandler:
    """Test the response generation handler."""

    def test_response_generation_validates_input(self):
        """Response generation should reject invalid input."""
        from handlers.response_generation import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestOrchestrationHandler:
    """Test the orchestration handler."""

    def test_orchestration_uses_local_fallback_without_sfn_arn(self):
        """Without STATE_MACHINE_ARN, orchestration should run locally."""
        from handlers import orchestration
        from models.agent import (
            ClassificationResult, Category, Priority, Sentiment,
            RetrievalResult, GenerationResult, ResponseDraft,
            OrchestrationResult, OrchestrationTrace
        )
        from datetime import datetime, timezone
        
        # Reset lazy-loaded orchestrator
        orchestration._orchestrator = None
        
        mock_result = OrchestrationResult(
            classification=ClassificationResult(
                category=Category.TECHNICAL,
                priority=Priority.MEDIUM,
                department="Support",
                sentiment=Sentiment.NEUTRAL,
                confidence=0.9,
                reasoning_snippet="Test"
            ),
            context=RetrievalResult(context_package=[], aggregate_confidence=0.8),
            generation=GenerationResult(
                primary_draft=ResponseDraft(
                    text="Test response",
                    citations=[],
                    confidence=0.7,
                    safety_flags=[]
                ),
                alternative_draft=None,
                suggested_next_steps=[],
                guardrail_triggered=False
            ),
            next_actions=["Review"],
            trace=OrchestrationTrace(
                classification_latency_ms=100,
                retrieval_latency_ms=50,
                generation_latency_ms=200,
                total_latency_ms=350,
                state="completed",
                started_at=datetime.now(timezone.utc),
                correlation_id="test-123"
            )
        )
        
        mock_service = MagicMock()
        mock_service.run.return_value = mock_result

        with patch.dict(os.environ, {"STATE_MACHINE_ARN": ""}):
            with patch.object(orchestration, '_get_orchestrator', return_value=mock_service):
                event = {
                    "body": json.dumps({
                        "title": "Test ticket",
                        "description": "Test description",
                        "customer_external_id": "CUST001"
                    })
                }
                result = orchestration.lambda_handler(event, None)
                
        assert result["statusCode"] == 200


class TestKbSyncHandler:
    """Test the KB sync handler."""

    def test_kb_sync_handles_event(self):
        """KB sync should process S3 events."""
        # Set environment vars first
        with patch.dict(os.environ, {
            "KNOWLEDGE_BASE_ID": "KB123",
            "DATA_SOURCE_ID": "DS456"
        }):
            # Patch boto3 before importing
            with patch("boto3.client") as mock_client_factory:
                mock_client = MagicMock()
                mock_client_factory.return_value = mock_client
                mock_client.start_ingestion_job.return_value = {
                    "ingestionJob": {"jobId": "test-123"}
                }

                # Force reimport to pick up patches
                import importlib
                import handlers.kb_sync
                importlib.reload(handlers.kb_sync)

                event = {
                    "detail": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test.pdf"}
                    }
                }
                result = handlers.kb_sync.lambda_handler(event, None)

                assert result["statusCode"] == 200
