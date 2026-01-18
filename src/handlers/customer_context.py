"""Handler for GET /tickets/{id}/context."""

import json
from typing import Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-loaded service to avoid import-time DB connections
_customer_service: Optional["CustomerService"] = None


def _get_customer_service():
    """Lazy-load CustomerService."""
    global _customer_service
    if _customer_service is None:
        from services.customer_service import CustomerService
        _customer_service = CustomerService()
    return _customer_service


def lambda_handler(event, context):
    """Return a 360-degree customer snapshot."""
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    external_id = query_params.get("customer_external_id") or path_params.get("id")
    if not external_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "customer_external_id is required"}),
        }

    context_obj = _get_customer_service().get_customer_context(external_id)
    if not context_obj:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Customer not found"}),
        }

    logger.info("Customer context served", extra={"external_id": external_id})
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": context_obj.model_dump_json(),
    }
