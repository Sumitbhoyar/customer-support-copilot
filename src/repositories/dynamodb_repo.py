"""DynamoDB repository for interaction logs."""

from typing import Dict, Any, List
import boto3


class DynamoDbRepository:
    """Provide basic query helpers."""

    def __init__(self, table_name: str):
        self.table = boto3.resource("dynamodb").Table(table_name)

    def put(self, item: Dict[str, Any]) -> None:
        """Insert an item."""
        self.table.put_item(Item=item)

    def query_recent(self, customer_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Query most recent interactions."""
        resp = self.table.query(
            KeyConditionExpression="customer_id = :cid",
            ExpressionAttributeValues={":cid": customer_id},
            ScanIndexForward=False,
            Limit=limit,
        )
        return resp.get("Items", [])
