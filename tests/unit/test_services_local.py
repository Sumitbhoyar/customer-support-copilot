"""
Service class tests with mocked AWS clients.

These tests validate service logic without connecting to AWS.

Run with: pytest tests/unit/test_services_local.py -v
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path to simulate Lambda environment
SRC_PATH = Path(__file__).parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestClassificationService:
    """Test ClassificationService."""

    @patch("services.classification_service.boto3")
    def test_service_instantiation(self, mock_boto3):
        """Service should instantiate without errors."""
        from services.classification_service import ClassificationService
        
        service = ClassificationService()
        assert service is not None

    @patch("services.classification_service.boto3")
    def test_service_has_classify_method(self, mock_boto3):
        """Service should have classify method."""
        from services.classification_service import ClassificationService
        
        service = ClassificationService()
        assert hasattr(service, "classify")
        assert callable(service.classify)

    @patch("services.classification_service.boto3")
    def test_heuristic_fallback(self, mock_boto3):
        """Service should have heuristic fallback for failed Bedrock calls."""
        from services.classification_service import ClassificationService
        from models.agent import TicketInput
        
        # Mock Bedrock to fail
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("Bedrock unavailable")
        
        service = ClassificationService()
        ticket = TicketInput(
            title="Billing question",
            description="I have a question about my bill",
            customer_external_id="CUST001"
        )
        
        # Should fall back to heuristic classification
        result = service.classify(ticket)
        assert result is not None
        assert result.confidence < 1.0  # Heuristic has lower confidence


class TestRetrievalService:
    """Test RetrievalService."""

    @patch("services.retrieval_service.CustomerService")
    @patch("services.retrieval_service.BedrockService")
    def test_service_instantiation(self, mock_bedrock, mock_customer):
        """Service should instantiate without errors."""
        from services.retrieval_service import RetrievalService
        
        service = RetrievalService()
        assert service is not None

    @patch("services.retrieval_service.CustomerService")
    @patch("services.retrieval_service.BedrockService")
    def test_service_has_build_context_method(self, mock_bedrock, mock_customer):
        """Service should have build_context method."""
        from services.retrieval_service import RetrievalService
        
        service = RetrievalService()
        assert hasattr(service, "build_context")
        assert callable(service.build_context)


class TestResponseService:
    """Test ResponseService."""

    @patch("services.response_service.boto3")
    def test_service_instantiation(self, mock_boto3):
        """Service should instantiate without errors."""
        from services.response_service import ResponseService
        
        service = ResponseService()
        assert service is not None

    @patch("services.response_service.boto3")
    def test_service_has_generate_response_method(self, mock_boto3):
        """Service should have generate_response method."""
        from services.response_service import ResponseService
        
        service = ResponseService()
        assert hasattr(service, "generate_response")
        assert callable(service.generate_response)


class TestOrchestrationService:
    """Test OrchestrationService."""

    @patch("services.orchestration_service.ClassificationService")
    @patch("services.orchestration_service.RetrievalService")
    @patch("services.orchestration_service.ResponseService")
    def test_service_instantiation(self, mock_response, mock_retrieval, mock_classification):
        """Service should instantiate without errors."""
        from services.orchestration_service import OrchestrationService
        
        service = OrchestrationService()
        assert service is not None

    @patch("services.orchestration_service.ClassificationService")
    @patch("services.orchestration_service.RetrievalService")
    @patch("services.orchestration_service.ResponseService")
    def test_service_has_run_method(self, mock_response, mock_retrieval, mock_classification):
        """Service should have run method."""
        from services.orchestration_service import OrchestrationService
        
        service = OrchestrationService()
        assert hasattr(service, "run")
        assert callable(service.run)


class TestCustomerService:
    """Test CustomerService."""

    @patch("services.customer_service.get_db_engine")
    @patch("services.customer_service.get_dynamodb")
    @patch("services.customer_service.boto3")
    def test_service_instantiation(self, mock_boto3, mock_ddb, mock_engine):
        """Service should instantiate without errors."""
        mock_engine.return_value = MagicMock()
        mock_ddb.return_value = MagicMock()
        
        from services.customer_service import CustomerService
        
        # Need to set env for dynamodb table
        with patch.dict(os.environ, {"INTERACTIONS_TABLE": "test-table"}):
            service = CustomerService()
            assert service is not None

    @patch("services.customer_service.get_db_engine")
    @patch("services.customer_service.get_dynamodb")
    @patch("services.customer_service.boto3")
    def test_service_has_get_customer_context_method(self, mock_boto3, mock_ddb, mock_engine):
        """Service should have get_customer_context method."""
        mock_engine.return_value = MagicMock()
        mock_ddb.return_value = MagicMock()
        
        from services.customer_service import CustomerService
        
        with patch.dict(os.environ, {"INTERACTIONS_TABLE": "test-table"}):
            service = CustomerService()
            assert hasattr(service, "get_customer_context")
            assert callable(service.get_customer_context)


class TestBedrockService:
    """Test BedrockService."""

    @patch("services.bedrock_service.boto3")
    def test_service_instantiation(self, mock_boto3):
        """Service should instantiate without errors."""
        from services.bedrock_service import BedrockService
        
        service = BedrockService()
        assert service is not None

    @patch("services.bedrock_service.boto3")
    def test_service_has_retrieve_method(self, mock_boto3):
        """Service should have retrieve method."""
        from services.bedrock_service import BedrockService
        
        service = BedrockService()
        assert hasattr(service, "retrieve")
        assert callable(service.retrieve)


class TestCacheService:
    """Test the LRU cache service."""

    def test_cache_instantiation(self):
        """Cache should instantiate without errors."""
        from utils.cache_service import LRUCache
        
        cache = LRUCache(max_size=10, ttl_seconds=60)
        assert cache is not None

    def test_cache_set_and_get(self):
        """Cache should store and retrieve values."""
        from utils.cache_service import LRUCache
        
        cache = LRUCache(max_size=10, ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """Cache should return None for missing keys."""
        from utils.cache_service import LRUCache
        
        cache = LRUCache(max_size=10, ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_cache_eviction(self):
        """Cache should evict oldest entries when full."""
        from utils.cache_service import LRUCache
        
        cache = LRUCache(max_size=2, ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
