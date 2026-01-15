"""
Single entrypoint Lambda that routes HTTP API requests to thin handler modules.

Why one Lambda?
- Keeps warm caches across routes (cheaper and faster).
- Simpler to deploy while still keeping code organized by delegating to modules.
"""

from typing import Callable, Dict, Tuple
import json

from . import health_check, ticket_ingestion, customer_context, kb_sync


def _response(status: int, body: Dict) -> Dict:
    """Format a JSON API Gateway HTTP API response."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    """
    Entry point invoked by API Gateway HTTP API.

    The event contains the HTTP method and path; we route it to the correct
    handler while keeping shared setup (logging, error handling) centralized.
    """
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("requestContext", {}).get("http", {}).get("path", "")
    route_key = f"{method.upper()} {path}"

    # Map route keys to handler callables. Using startswith for path params.
    route_table: Tuple[Tuple[str, Callable], ...] = (
        ("GET /health", health_check.lambda_handler),
        ("POST /tickets/", ticket_ingestion.feedback_handler),  # more specific feedback first
        ("GET /tickets/", customer_context.lambda_handler),
        ("POST /tickets", ticket_ingestion.lambda_handler),
        ("POST /tickets/", ticket_ingestion.lambda_handler),  # fallback for other POST paths
        ("POST /kb/sync", kb_sync.lambda_handler),
    )

    for prefix, handler in route_table:
        if route_key.startswith(prefix):
            return handler(event, context)

    return _response(404, {"message": "Route not found", "route": route_key})
