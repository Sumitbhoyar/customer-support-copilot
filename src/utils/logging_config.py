"""Structured logger setup shared across Lambdas."""

import logging
from pythonjsonlogger import jsonlogger


def get_logger(name: str) -> logging.Logger:
    """
    Configure a JSON logger once and reuse it.

    Keeping logging lean reduces CloudWatch costs while retaining context.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(levelname)s %(name)s %(message)s %(asctime)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
