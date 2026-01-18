"""Structured logger setup shared across Lambdas.

Uses AWS Lambda Powertools Logger for structured JSON logging.
This is included in the Powertools layer and provides:
- Automatic correlation IDs
- JSON formatted output for CloudWatch
- Low overhead
"""

from aws_lambda_powertools import Logger

# Cache loggers by name to avoid creating duplicates
_loggers: dict = {}


def get_logger(name: str) -> Logger:
    """
    Get or create a Powertools Logger.

    Keeping logging lean reduces CloudWatch costs while retaining context.
    Powertools Logger automatically formats as JSON for CloudWatch Insights.
    """
    if name not in _loggers:
        _loggers[name] = Logger(service=name)
    return _loggers[name]
