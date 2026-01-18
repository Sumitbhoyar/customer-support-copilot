"""
KB sync handler triggered by S3 events (via EventBridge) or manual POST /kb/sync.
"""

import json
import os
import boto3

from utils.logging_config import get_logger

logger = get_logger(__name__)
client = boto3.client("bedrock-agent")


def lambda_handler(event, context):
    """Start a Bedrock ingestion job for the configured KB data source."""
    knowledge_base_id = os.environ["KNOWLEDGE_BASE_ID"]
    data_source_id = os.environ["DATA_SOURCE_ID"]

    try:
        resp = client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
        )
        job_id = resp.get("ingestionJob", {}).get("ingestionJobId")
        logger.info("KB ingestion started", extra={"job_id": job_id})
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"job_id": job_id, "status": "started"}),
        }
    except Exception as exc:
        logger.exception("KB sync failed")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "KB sync failed", "error": str(exc)}),
        }
