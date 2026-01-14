"""S3 repository for KB documents."""

from typing import Iterable
import boto3


class S3Repository:
    """Minimal helper around S3 for uploads/listing."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = boto3.client("s3")

    def upload_text(self, key: str, content: str) -> None:
        """Upload text content (defaults to Intelligent-Tiering)."""
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content.encode(),
            StorageClass="INTELLIGENT_TIERING",
        )

    def list_keys(self, prefix: str = "") -> Iterable[str]:
        """List object keys under a prefix."""
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for item in page.get("Contents", []):
                yield item["Key"]
