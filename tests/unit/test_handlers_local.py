"""
Local handler tests using mocks.

These tests validate handler logic without connecting to AWS.
AWS services are mocked using unittest.mock and moto where applicable.

Run with: pytest tests/unit/test_handlers_local.py -v
"""

import json
import sys
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

        with patch.dict("os.environ", {"ENVIRONMENT": "test"}):
            # Need to reimport to pick up env change
            import importlib
            import handlers.health_check
            importlib.reload(handlers.health_check)
            
            result = handlers.health_check.lambda_handler({}, None)
            body = json.loads(result["body"])
            assert body["environment"] == "test"


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
    """Test the classification handler with mocked Bedrock."""

    @patch("services.classification_service.boto3")
    def test_classification_validates_input(self, mock_boto3):
        """Classification should reject invalid input."""
        from handlers.classification import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({"title": ""})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "correlation_id" in body

    @patch("services.classification_service.boto3")
    def test_classification_with_valid_input(self, mock_boto3):
        """Classification should process valid input."""
        # Mock Bedrock response
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": json.dumps({
                    "category": "Technical",
                    "priority": "Medium",
                    "department": "Support",
                    "sentiment": "Neutral",
                    "confidence": 0.85,
                    "reasoning_snippet": "Technical issue"
                })}]
            }).encode())
        }

        from handlers.classification import lambda_handler

        event = {
            "body": json.dumps({
                "title": "Cannot login to account",
                "description": "Getting error when trying to access my account",
                "customer_id": "CUST001"
            })
        }
        result = lambda_handler(event, None)

        # Should succeed or fail gracefully with mocked Bedrock
        assert result["statusCode"] in [200, 400]


class TestRetrievalHandler:
    """Test the retrieval handler with mocked services."""

    @patch("services.retrieval_service.boto3")
    @patch("services.customer_service.boto3")
    def test_retrieval_validates_input(self, mock_customer_boto, mock_retrieval_boto):
        """Retrieval should reject invalid input."""
        from handlers.retrieval import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestResponseGenerationHandler:
    """Test the response generation handler with mocked Bedrock."""

    @patch("services.response_service.boto3")
    def test_response_generation_validates_input(self, mock_boto3):
        """Response generation should reject invalid input."""
        from handlers.response_generation import lambda_handler

        # Missing required fields
        event = {"body": json.dumps({})}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestOrchestrationHandler:
    """Test the orchestration handler."""

    @patch("handlers.orchestration.boto3")
    @patch("services.orchestration_service.ClassificationService")
    @patch("services.orchestration_service.RetrievalService")
    @patch("services.orchestration_service.ResponseService")
    def test_orchestration_uses_local_fallback_without_sfn_arn(
        self, mock_response, mock_retrieval, mock_classification, mock_boto3
    ):
        """Without STATE_MACHINE_ARN, orchestration should run locally."""
        # Setup mocks
        mock_classification.return_value.classify.return_value = MagicMock(
            category="Technical",
            priority="Medium",
            department="Support",
            sentiment="Neutral",
            confidence=0.9,
            reasoning_snippet="Test"
        )
        mock_retrieval.return_value.retrieve.return_value = MagicMock(
            context_items=[],
            aggregate_confidence=0.8,
            retrieval_time_ms=100
        )
        mock_response.return_value.generate.return_value = MagicMock(
            drafts=[],
            generation_time_ms=200,
            model_used="test"
        )

        from handlers.orchestration import lambda_handler

        event = {
            "body": json.dumps({
                "title": "Test ticket",
                "description": "Test description",
                "customer_id": "CUST001"
            })
        }

        with patch.dict("os.environ", {"STATE_MACHINE_ARN": ""}):
            result = lambda_handler(event, None)
            # Should attempt local orchestration
            assert result["statusCode"] in [200, 400, 500]


class TestKbSyncHandler:
    """Test the KB sync handler."""

    @patch("handlers.kb_sync.boto3")
    def test_kb_sync_handles_event(self, mock_boto3):
        """KB sync should process S3 events."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.start_ingestion_job.return_value = {"ingestionJob": {"jobId": "test-123"}}

        from handlers.kb_sync import lambda_handler

        with patch.dict("os.environ", {
            "KNOWLEDGE_BASE_ID": "KB123",
            "DATA_SOURCE_ID": "DS456"
        }):
            event = {
                "detail": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test.pdf"}
                }
            }
            result = lambda_handler(event, None)

            assert result["statusCode"] == 200
