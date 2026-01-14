"""Handler for GET /tickets/{id}/context."""

import json

from src.services.customer_service import CustomerService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
customer_service = CustomerService()


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

    context_obj = customer_service.get_customer_context(external_id)
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
