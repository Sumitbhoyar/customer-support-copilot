"""Lightweight health check handler."""

import os
import json
from datetime import datetime, timezone


def lambda_handler(event, context):
    """Return a simple 200 response to verify the stack is alive."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "ok",
                "environment": os.environ.get("ENVIRONMENT", "dev"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
    }
