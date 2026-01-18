"""
Customer Context Service.

Retrieves and aggregates customer data from PostgreSQL and DynamoDB
to build a 360-degree customer view. To keep the sample deployable
without a live database, the DB calls are guarded and fall back to
safe defaults when credentials are missing.
"""

from __future__ import annotations

import os
from typing import Optional
from datetime import datetime, timedelta

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from models.customer import CustomerContext
from utils.logging_config import get_logger
from utils.cache_service import LRUCache

logger = get_logger(__name__)

# Connection pooling for Lambda reuse.
_engine = None
_dynamodb = None

# In-memory cache (survives warm Lambda invocations).
customer_cache = LRUCache(max_size=100, ttl_seconds=300)


def get_db_engine():
    """Get or create SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            secret_arn = os.environ.get("DB_SECRET_ARN")
            if secret_arn:
                db_url = _secret_to_db_url(secret_arn)
            else:
                logger.warning("DATABASE_URL not set; DB calls will be skipped")
                return None
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=1,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


def _secret_to_db_url(secret_arn: str) -> Optional[str]:
    """Build a SQLAlchemy URL from an RDS secret."""
    try:
        sm = boto3.client("secretsmanager")
        secret_value = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
        import json

        secret = json.loads(secret_value)
        host = secret.get("host")
        port = secret.get("port", 5432)
        username = secret.get("username")
        password = secret.get("password")
        dbname = secret.get("dbname", "postgres")
        if not (host and username and password):
            return None
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
    except Exception as exc:
        logger.warning("Failed to load DB secret", extra={"error": str(exc)})
        return None


def get_dynamodb():
    """Get or create DynamoDB resource."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


class CustomerService:
    """Service for customer context retrieval."""

    def __init__(self, interactions_table_name: str = None):
        table_name = interactions_table_name or os.environ.get(
            "INTERACTIONS_TABLE", "customer-interactions"
        )
        self.engine = get_db_engine()
        self.dynamodb = get_dynamodb()
        self.interactions_table = self.dynamodb.Table(table_name)

    def get_customer_context(
        self,
        external_id: str,
        include_orders: bool = True,
        include_interactions: bool = True,
    ) -> Optional[CustomerContext]:
        """Build 360-degree customer context with caching."""
        cache_key = f"customer:{external_id}"
        cached = customer_cache.get(cache_key)
        if cached:
            logger.info("Customer cache hit", extra={"external_id": external_id})
            return cached

        # Safeguard when DB isn't configured.
        if not self.engine:
            return CustomerContext(
                customer_id="placeholder",
                external_id=external_id,
                name="Sample User",
                email="sample@example.com",
                company=None,
                tier="standard",
                lifetime_value=0.0,
                total_orders=0,
                recent_orders=[],
                open_tickets=0,
                avg_sentiment=0.0,
                last_interaction=None,
                is_high_value=False,
                churn_risk="low",
            )

        try:
            customer_data = self._get_customer_from_db(external_id)
            if not customer_data:
                return None

            recent_orders = []
            total_orders = 0
            if include_orders:
                orders_data = self._get_recent_orders(customer_data["customer_id"])
                recent_orders = orders_data["orders"]
                total_orders = orders_data["total_count"]

            interactions = []
            avg_sentiment = 0.0
            last_interaction = None
            if include_interactions:
                interactions_data = self._get_interactions(customer_data["customer_id"])
                interactions = interactions_data["interactions"]
                avg_sentiment = interactions_data["avg_sentiment"]
                last_interaction = interactions_data["last_interaction"]

            context = CustomerContext(
                customer_id=str(customer_data["customer_id"]),
                external_id=external_id,
                name=customer_data["name"],
                email=customer_data["email"],
                company=customer_data.get("company"),
                tier=customer_data.get("tier", "standard"),
                lifetime_value=float(customer_data.get("lifetime_value", 0)),
                total_orders=total_orders,
                recent_orders=recent_orders,
                open_tickets=0,
                avg_sentiment=avg_sentiment,
                last_interaction=last_interaction,
                is_high_value=float(customer_data.get("lifetime_value", 0)) > 10000,
                churn_risk=self._calculate_churn_risk(
                    avg_sentiment, last_interaction, customer_data.get("tier", "standard")
                ),
            )

            customer_cache.set(cache_key, context)
            logger.info(
                "Customer context built",
                extra={
                    "external_id": external_id,
                    "tier": context.tier,
                    "is_high_value": context.is_high_value,
                },
            )
            return context
        except Exception as exc:
            logger.error(
                "Failed to get customer context",
                extra={"external_id": external_id, "error": str(exc)},
            )
            return None

    def _get_customer_from_db(self, external_id: str) -> Optional[dict]:
        """Fetch customer data from PostgreSQL."""
        query = text(
            """
            SELECT customer_id, external_id, email, name, company, tier, lifetime_value
            FROM customers
            WHERE external_id = :external_id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"external_id": external_id})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        return None

    def _get_recent_orders(self, customer_id: str, limit: int = 5) -> dict:
        """Fetch recent orders from PostgreSQL."""
        count_query = text(
            """
            SELECT COUNT(*) as total FROM orders WHERE customer_id = :customer_id
        """
        )

        orders_query = text(
            """
            SELECT order_id, order_number, status, total_amount, order_date
            FROM orders
            WHERE customer_id = :customer_id
            ORDER BY order_date DESC
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            total = conn.execute(count_query, {"customer_id": customer_id}).scalar()
            result = conn.execute(orders_query, {"customer_id": customer_id, "limit": limit})
            orders = [dict(row._mapping) for row in result]

        return {"total_count": total or 0, "orders": orders}

    def _get_interactions(self, customer_id: str, days: int = 90) -> dict:
        """Fetch interaction history from DynamoDB."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            response = self.interactions_table.query(
                KeyConditionExpression="customer_id = :cid AND #ts > :cutoff",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":cid": customer_id, ":cutoff": cutoff},
                ScanIndexForward=False,
                Limit=20,
            )

            items = response.get("Items", [])
            sentiments = [float(i.get("sentiment", 0)) for i in items if "sentiment" in i]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            last_interaction = None
            if items:
                last_interaction = datetime.fromisoformat(items[0]["timestamp"])

            return {
                "interactions": items[:10],
                "avg_sentiment": round(avg_sentiment, 2),
                "last_interaction": last_interaction,
            }
        except Exception as exc:
            logger.warning("Failed to fetch interactions", extra={"error": str(exc)})
            return {"interactions": [], "avg_sentiment": 0.0, "last_interaction": None}

    def _calculate_churn_risk(
        self, avg_sentiment: float, last_interaction: Optional[datetime], tier: str
    ) -> str:
        """Calculate churn risk based on engagement signals."""
        risk_score = 0

        if avg_sentiment < -0.3:
            risk_score += 3
        elif avg_sentiment < 0:
            risk_score += 1

        if last_interaction:
            days_since = (datetime.utcnow() - last_interaction).days
            if days_since > 60:
                risk_score += 3
            elif days_since > 30:
                risk_score += 1
        else:
            risk_score += 2

        if tier == "enterprise" and risk_score > 0:
            risk_score += 1

        if risk_score >= 4:
            return "high"
        if risk_score >= 2:
            return "medium"
        return "low"
