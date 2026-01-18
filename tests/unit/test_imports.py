"""
Import validation tests.

These tests ensure all modules can be imported successfully, catching
issues like missing dependencies or circular imports BEFORE deployment.

Run with: pytest tests/unit/test_imports.py -v
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# Add src to path to simulate Lambda environment
SRC_PATH = Path(__file__).parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestHandlerImports:
    """Verify all handler modules can be imported without errors."""

    @pytest.mark.parametrize("module_name", [
        "handlers.main",
        "handlers.health_check",
        "handlers.ticket_ingestion",
        "handlers.customer_context",
        "handlers.kb_sync",
        "handlers.classification",
        "handlers.retrieval",
        "handlers.response_generation",
        "handlers.orchestration",
    ])
    def test_handler_import(self, module_name: str):
        """Each handler module should import without errors."""
        try:
            module = importlib.import_module(module_name)
            assert hasattr(module, "lambda_handler"), f"{module_name} missing lambda_handler"
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestServiceImports:
    """Verify all service modules can be imported."""

    @pytest.mark.parametrize("module_name", [
        "services.bedrock_service",
        "services.customer_service",
        "services.ticket_service",
        "services.classification_service",
        "services.retrieval_service",
        "services.response_service",
        "services.orchestration_service",
    ])
    def test_service_import(self, module_name: str):
        """Each service module should import without errors."""
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestModelImports:
    """Verify all model modules can be imported."""

    @pytest.mark.parametrize("module_name", [
        "models.agent",
        "models.customer",
        "models.knowledge",
        "models.response",
        "models.ticket",
    ])
    def test_model_import(self, module_name: str):
        """Each model module should import without errors."""
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestUtilImports:
    """Verify all utility modules can be imported."""

    @pytest.mark.parametrize("module_name", [
        "utils.logging_config",
        "utils.cache_service",
        "utils.error_handling",
        "utils.validators",
    ])
    def test_util_import(self, module_name: str):
        """Each utility module should import without errors."""
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestNoSrcPrefix:
    """Ensure no modules use 'from src.' imports (breaks in Lambda)."""

    def test_no_src_prefix_in_handlers(self):
        """Handler files should not have 'from src.' imports."""
        handlers_dir = SRC_PATH / "handlers"
        for py_file in handlers_dir.glob("*.py"):
            content = py_file.read_text()
            assert "from src." not in content, f"{py_file.name} contains 'from src.' import"
            assert "import src." not in content, f"{py_file.name} contains 'import src.' import"

    def test_no_src_prefix_in_services(self):
        """Service files should not have 'from src.' imports."""
        services_dir = SRC_PATH / "services"
        for py_file in services_dir.glob("*.py"):
            content = py_file.read_text()
            assert "from src." not in content, f"{py_file.name} contains 'from src.' import"
            assert "import src." not in content, f"{py_file.name} contains 'import src.' import"

    def test_no_src_prefix_in_models(self):
        """Model files should not have 'from src.' imports."""
        models_dir = SRC_PATH / "models"
        for py_file in models_dir.glob("*.py"):
            content = py_file.read_text()
            assert "from src." not in content, f"{py_file.name} contains 'from src.' import"
            assert "import src." not in content, f"{py_file.name} contains 'import src.' import"

    def test_no_src_prefix_in_utils(self):
        """Utility files should not have 'from src.' imports."""
        utils_dir = SRC_PATH / "utils"
        for py_file in utils_dir.glob("*.py"):
            content = py_file.read_text()
            assert "from src." not in content, f"{py_file.name} contains 'from src.' import"
            assert "import src." not in content, f"{py_file.name} contains 'import src.' import"
