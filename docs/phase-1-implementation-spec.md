# AI Customer Support Platform - Phase 1 Implementation Spec
## Cursor AI Implementation Guide

**Project:** AI-Assisted Customer Support & Helpdesk Automation  
**Phase:** 1 - Foundation & Integration  
**Duration:** 8 weeks  
**Architecture:** Serverless, Event-Driven, Cost-Optimized  
**IaC Tool:** AWS CDK (Python)

---

## 1. PROJECT OVERVIEW

### 1.1 Objective
Establish a production-ready RAG pipeline with knowledge base ingestion, customer context integration, and ticketing system API—optimized for low cost without compromising the core architecture.

### 1.2 Cost Optimization Strategy

| Original Design | Cost-Optimized Alternative | Savings |
|-----------------|---------------------------|---------|
| RDS Aurora Serverless | RDS PostgreSQL (db.t3.micro free tier → db.t3.small) | ~70% |
| ElastiCache Redis | DynamoDB DAX or in-Lambda caching (LRU) | ~80% |
| OpenSearch for vector DB | Bedrock KB with built-in vector store (no extra DB) | ~60% |
| Multiple Lambda functions | Consolidated Lambda with routing | ~40% |
| API Gateway REST | API Gateway HTTP (v2) | ~70% |
| Step Functions Standard | Step Functions Express (for short workflows) | ~80% |

**Estimated Monthly Cost (Phase 1):** $150-250/month (vs. $800-1000 original)

### 1.3 Technology Stack

```
Infrastructure:     AWS CDK (Python)
Runtime:            Python 3.12
AI/ML:              Amazon Bedrock (Claude 3.5 Haiku, Titan Embeddings)
Database:           PostgreSQL (RDS), DynamoDB
Storage:            S3
API:                API Gateway HTTP API (v2)
Compute:            Lambda (ARM64 for cost savings)
Queue:              SQS Standard
Events:             EventBridge
Monitoring:         CloudWatch (basic)
```

---

## 2. PROJECT STRUCTURE

```
ai-support-platform/
├── .cursorrules                    # Cursor AI coding rules
├── README.md                       # Project documentation
├── requirements.txt                # Python dependencies
├── cdk.json                        # CDK configuration
├── app.py                          # CDK app entry point
│
├── infrastructure/                 # CDK Infrastructure Code
│   ├── __init__.py
│   ├── main_stack.py              # Main CDK stack
│   ├── constructs/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py      # Bedrock KB construct
│   │   ├── data_layer.py          # RDS + DynamoDB construct
│   │   ├── api_layer.py           # API Gateway + Lambda construct
│   │   └── event_pipeline.py      # S3 → EventBridge → Lambda
│   └── config/
│       ├── __init__.py
│       └── settings.py            # Environment configuration
│
├── src/                           # Application Source Code
│   ├── __init__.py
│   ├── handlers/                  # Lambda handlers
│   │   ├── __init__.py
│   │   ├── ticket_ingestion.py    # Ticket API handler
│   │   ├── kb_sync.py             # Knowledge base sync handler
│   │   ├── customer_context.py    # Customer 360 handler
│   │   └── health_check.py        # Health check endpoint
│   │
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── bedrock_service.py     # Bedrock KB interactions
│   │   ├── customer_service.py    # Customer data service
│   │   ├── ticket_service.py      # Ticket processing service
│   │   └── cache_service.py       # In-memory LRU cache
│   │
│   ├── models/                    # Data models (Pydantic)
│   │   ├── __init__.py
│   │   ├── ticket.py              # Ticket model
│   │   ├── customer.py            # Customer model
│   │   ├── knowledge.py           # KB document model
│   │   └── response.py            # API response models
│   │
│   ├── repositories/              # Data access layer
│   │   ├── __init__.py
│   │   ├── postgres_repo.py       # PostgreSQL repository
│   │   ├── dynamodb_repo.py       # DynamoDB repository
│   │   └── s3_repo.py             # S3 document repository
│   │
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── logging_config.py      # Structured logging
│       ├── error_handling.py      # Exception handlers
│       └── validators.py          # Input validation
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_ticket_service.py
│   │   ├── test_bedrock_service.py
│   │   └── test_customer_service.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_kb_retrieval.py
│   └── fixtures/
│       ├── sample_tickets.json
│       └── sample_documents.json
│
├── scripts/                       # Utility scripts
│   ├── seed_knowledge_base.py     # Initial KB document upload
│   ├── seed_customer_data.py      # Sample customer data
│   └── test_local.py              # Local testing script
│
├── docs/                          # Documentation
│   ├── architecture.md            # Architecture decisions
│   ├── api_spec.yaml              # OpenAPI specification
│   └── runbook.md                 # Operations runbook
│
└── sample_data/                   # Sample data for testing
    ├── knowledge_docs/            # Sample KB documents
    │   ├── faq.pdf
    │   ├── product_guide.html
    │   └── troubleshooting.md
    └── customers/                 # Sample customer data
        └── customers.json
```

---

## 3. CURSOR RULES FILE

Create `.cursorrules` in project root:

```
# ============================================
# AI Customer Support Platform - Cursor Rules
# ============================================

# Project Context
- This is an AWS serverless application for AI-assisted customer support
- We use AWS CDK (Python) for infrastructure as code
- Runtime is Python 3.12 with AWS Lambda (ARM64 architecture)
- Primary AI service is Amazon Bedrock with Claude 3.5 Haiku (cost-optimized)

# Code Style & Standards
- Follow PEP 8 style guidelines strictly
- Use type hints for all function parameters and return values
- Use Pydantic v2 for data validation and models
- Use async/await patterns where beneficial for I/O operations
- Maximum line length: 100 characters
- Use descriptive variable names (no single letters except loop counters)

# AWS CDK Conventions
- Use L2 constructs (higher-level) when available
- Apply least-privilege IAM policies
- Use environment variables for configuration, never hardcode secrets
- Tag all resources with: Project, Environment, CostCenter
- Use removal_policy=RETAIN for production databases, DESTROY for dev

# Lambda Best Practices
- Use ARM64 architecture (Graviton2) for 20% cost savings
- Keep handler functions thin; delegate to service classes
- Use Lambda Powertools for logging, tracing, metrics
- Implement connection pooling for database connections
- Set appropriate memory (512MB default) and timeout (30s default)
- Use Lambda layers for shared dependencies

# Error Handling
- Use custom exception classes in src/utils/error_handling.py
- Always log errors with context before re-raising
- Return structured error responses with correlation IDs
- Implement circuit breaker pattern for external service calls

# Database Access
- Use SQLAlchemy Core (not ORM) for PostgreSQL - lightweight
- Use boto3 resource API for DynamoDB
- Always use parameterized queries (no string concatenation)
- Implement repository pattern for data access abstraction

# Testing
- Write unit tests for all service classes
- Use pytest with pytest-asyncio for async tests
- Mock AWS services using moto library
- Maintain >80% code coverage for src/ directory

# Security
- Never log sensitive data (PII, credentials, tokens)
- Use AWS Secrets Manager for database credentials
- Validate all input using Pydantic models
- Implement request throttling at API Gateway level

# Cost Optimization (IMPORTANT)
- Prefer Bedrock Claude Haiku over Sonnet for simple tasks
- Use S3 Intelligent-Tiering for document storage
- Implement in-memory LRU cache before external cache calls
- Use SQS Standard (not FIFO) unless ordering is critical
- Use API Gateway HTTP API (v2), not REST API
- Batch DynamoDB operations where possible

# Documentation
- Add docstrings to all public functions and classes
- Update README.md when adding new features
- Keep API spec (docs/api_spec.yaml) in sync with implementation
```

---

## 4. IMPLEMENTATION SPECIFICATIONS

### 4.1 AWS Bedrock Knowledge Base

**File:** `infrastructure/constructs/knowledge_base.py`

**Requirements:**
- Create S3 bucket for knowledge base documents
- Configure Bedrock Knowledge Base with:
  - Embedding model: amazon.titan-embed-text-v2:0
  - Chunking strategy: Fixed-size, 512 tokens, 50-token overlap
  - Vector store: Bedrock managed (OpenSearch Serverless - included)
- Create IAM role for Bedrock KB access to S3
- Set up EventBridge rule: S3 PutObject → Lambda → Sync KB

**Data Source Configuration:**
```python
chunking_configuration = {
    "chunkingStrategy": "FIXED_SIZE",
    "fixedSizeChunkingConfiguration": {
        "maxTokens": 512,
        "overlapPercentage": 10  # ~50 tokens overlap
    }
}
```

**Supported Document Types:**
- PDF (.pdf)
- HTML (.html, .htm)
- Plain text (.txt, .md)
- Word documents (.docx)
- CSV (.csv)

**Lambda Sync Handler Logic:**
1. Triggered by S3 PutObject/DeleteObject events
2. Call Bedrock StartIngestionJob API
3. Log job ID and status
4. Store sync metadata in DynamoDB (audit trail)

---

### 4.2 Customer Context Integration

**File:** `infrastructure/constructs/data_layer.py`

**PostgreSQL Schema (RDS):**

```sql
-- Customer accounts table
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(100) UNIQUE NOT NULL,  -- From ticketing system
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'standard',  -- standard, premium, enterprise
    lifetime_value DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer orders/purchases
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(customer_id),
    order_number VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(12, 2),
    order_date TIMESTAMP NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX idx_customers_external_id ON customers(external_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date DESC);
```

**DynamoDB Table (Interaction Logs):**

```python
interaction_logs_table = {
    "TableName": "customer-interactions",
    "KeySchema": [
        {"AttributeName": "customer_id", "KeyType": "HASH"},
        {"AttributeName": "timestamp", "KeyType": "RANGE"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "customer_id", "AttributeType": "S"},
        {"AttributeName": "timestamp", "AttributeType": "S"}
    ],
    "BillingMode": "PAY_PER_REQUEST",  # Cost-optimized: on-demand
    "TimeToLiveSpecification": {
        "AttributeName": "ttl",
        "Enabled": True  # Auto-expire old logs after 90 days
    }
}
```

**Customer 360 Response Model:**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class CustomerContext(BaseModel):
    customer_id: str
    external_id: str
    name: str
    email: str
    company: Optional[str]
    tier: str  # standard, premium, enterprise
    lifetime_value: float

    # Aggregated data
    total_orders: int
    recent_orders: List[dict]  # Last 5 orders
    open_tickets: int
    avg_sentiment: float  # -1 to 1
    last_interaction: Optional[datetime]

    # Computed flags
    is_high_value: bool  # LTV > threshold
    churn_risk: str  # low, medium, high
```

---

### 4.3 Ticketing System Integration

**File:** `infrastructure/constructs/api_layer.py`

**API Gateway HTTP API Endpoints:**

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | /tickets | ticket_ingestion | Receive new ticket from ticketing system |
| GET | /tickets/{id}/context | customer_context | Get customer 360 + KB suggestions |
| POST | /tickets/{id}/feedback | ticket_ingestion | Record agent feedback on suggestions |
| GET | /health | health_check | Health check endpoint |
| POST | /kb/sync | kb_sync | Trigger manual KB sync |

**Ticket Ingestion Request:**

```python
class TicketRequest(BaseModel):
    ticket_id: str
    external_ticket_id: str  # ID from source ticketing system
    customer_external_id: str
    subject: str
    description: str
    channel: str  # email, chat, phone, web
    priority: Optional[str] = "medium"
    metadata: Optional[dict] = {}
    created_at: datetime

class TicketResponse(BaseModel):
    ticket_id: str
    status: str  # received, processing, ready
    customer_context: Optional[CustomerContext]
    kb_suggestions: Optional[List[KBSuggestion]]
    processing_time_ms: int
    correlation_id: str
```

**SQS Queue Configuration:**

```python
ticket_queue = {
    "QueueName": "ticket-ingestion-queue",
    "VisibilityTimeoutSeconds": 60,
    "MessageRetentionPeriod": 1209600,  # 14 days
    "ReceiveMessageWaitTimeSeconds": 20,  # Long polling
    "DeadLetterTargetArn": dlq_arn,
    "maxReceiveCount": 3  # Retry 3 times before DLQ
}
```

---

## 5. SERVICE IMPLEMENTATIONS

### 5.1 Bedrock Service

**File:** `src/services/bedrock_service.py`

```python
"""
Amazon Bedrock Knowledge Base Service

Handles interactions with Bedrock KB for document retrieval
and response generation.
"""

import boto3
from typing import List, Optional
from functools import lru_cache
import hashlib

from src.models.knowledge import KBQuery, KBResult
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BedrockService:
    """Service for Bedrock Knowledge Base operations."""

    def __init__(
        self,
        knowledge_base_id: str,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "eu-west-2"
    ):
        self.knowledge_base_id = knowledge_base_id
        self.model_id = model_id
        self.bedrock_agent = boto3.client(
            "bedrock-agent-runtime",
            region_name=region
        )
        self._cache = {}  # Simple in-memory cache

    def retrieve(
        self,
        query: str,
        max_results: int = 3,
        min_score: float = 0.5
    ) -> List[KBResult]:
        """
        Retrieve relevant documents from Knowledge Base.

        Args:
            query: Search query text
            max_results: Maximum number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            List of KBResult with document chunks and scores
        """
        cache_key = self._get_cache_key(query, max_results)

        # Check cache first
        if cache_key in self._cache:
            logger.info("KB cache hit", query_hash=cache_key[:8])
            return self._cache[cache_key]

        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                        "overrideSearchType": "HYBRID"  # Vector + keyword
                    }
                }
            )

            results = []
            for item in response.get("retrievalResults", []):
                score = item.get("score", 0)
                if score >= min_score:
                    results.append(KBResult(
                        content=item["content"]["text"],
                        score=score,
                        source=item.get("location", {}).get("s3Location", {}).get("uri", ""),
                        metadata=item.get("metadata", {})
                    ))

            # Cache results
            self._cache[cache_key] = results
            logger.info("KB retrieval complete", 
                       query_length=len(query), 
                       results_count=len(results))

            return results

        except Exception as e:
            logger.error("KB retrieval failed", error=str(e), query=query[:50])
            raise

    def retrieve_and_generate(
        self,
        query: str,
        customer_context: Optional[str] = None,
        max_results: int = 3
    ) -> dict:
        """
        Retrieve context and generate response using Bedrock.

        This uses the RetrieveAndGenerate API which combines
        retrieval with Claude generation in a single call.
        """
        input_text = query
        if customer_context:
            input_text = f"Customer Context: {customer_context}\n\nQuery: {query}"

        try:
            response = self.bedrock_agent.retrieve_and_generate(
                input={"text": input_text},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": self.knowledge_base_id,
                        "modelArn": f"arn:aws:bedrock:eu-west-2::foundation-model/{self.model_id}",
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {
                                "numberOfResults": max_results
                            }
                        },
                        "generationConfiguration": {
                            "inferenceConfig": {
                                "textInferenceConfig": {
                                    "maxTokens": 500,
                                    "temperature": 0.1,
                                    "topP": 0.9
                                }
                            }
                        }
                    }
                }
            )

            return {
                "generated_text": response["output"]["text"],
                "citations": [
                    {
                        "text": c.get("generatedResponsePart", {}).get("textResponsePart", {}).get("text", ""),
                        "sources": [
                            ref.get("location", {}).get("s3Location", {}).get("uri", "")
                            for ref in c.get("retrievedReferences", [])
                        ]
                    }
                    for c in response.get("citations", [])
                ]
            }

        except Exception as e:
            logger.error("Retrieve and generate failed", error=str(e))
            raise

    def _get_cache_key(self, query: str, max_results: int) -> str:
        """Generate cache key from query parameters."""
        content = f"{query}:{max_results}"
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("KB cache cleared")
```

---

### 5.2 Customer Service

**File:** `src/services/customer_service.py`

```python
"""
Customer Context Service

Retrieves and aggregates customer data from PostgreSQL
and DynamoDB to build a 360-degree customer view.
"""

import os
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from src.models.customer import CustomerContext
from src.utils.logging_config import get_logger
from src.utils.cache_service import LRUCache

logger = get_logger(__name__)

# Connection pooling for Lambda reuse
_engine = None
_dynamodb = None

# In-memory cache (survives warm Lambda invocations)
customer_cache = LRUCache(max_size=100, ttl_seconds=300)


def get_db_engine():
    """Get or create SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        db_url = os.environ.get("DATABASE_URL")
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=1,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300
        )
    return _engine


def get_dynamodb():
    """Get or create DynamoDB resource."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


class CustomerService:
    """Service for customer context retrieval."""

    def __init__(self, interactions_table_name: str = "customer-interactions"):
        self.engine = get_db_engine()
        self.dynamodb = get_dynamodb()
        self.interactions_table = self.dynamodb.Table(interactions_table_name)

    def get_customer_context(
        self,
        external_id: str,
        include_orders: bool = True,
        include_interactions: bool = True
    ) -> Optional[CustomerContext]:
        """
        Build 360-degree customer context.

        Args:
            external_id: Customer ID from ticketing system
            include_orders: Include recent orders
            include_interactions: Include interaction history

        Returns:
            CustomerContext with aggregated data
        """
        # Check cache first
        cache_key = f"customer:{external_id}"
        cached = customer_cache.get(cache_key)
        if cached:
            logger.info("Customer cache hit", external_id=external_id)
            return cached

        try:
            # Get customer base data from PostgreSQL
            customer_data = self._get_customer_from_db(external_id)
            if not customer_data:
                logger.warning("Customer not found", external_id=external_id)
                return None

            # Get recent orders
            recent_orders = []
            total_orders = 0
            if include_orders:
                orders_data = self._get_recent_orders(customer_data["customer_id"])
                recent_orders = orders_data["orders"]
                total_orders = orders_data["total_count"]

            # Get interaction history from DynamoDB
            interactions = []
            avg_sentiment = 0.0
            last_interaction = None
            if include_interactions:
                interactions_data = self._get_interactions(customer_data["customer_id"])
                interactions = interactions_data["interactions"]
                avg_sentiment = interactions_data["avg_sentiment"]
                last_interaction = interactions_data["last_interaction"]

            # Build context
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
                open_tickets=0,  # TODO: integrate with ticket count
                avg_sentiment=avg_sentiment,
                last_interaction=last_interaction,
                is_high_value=float(customer_data.get("lifetime_value", 0)) > 10000,
                churn_risk=self._calculate_churn_risk(
                    avg_sentiment, 
                    last_interaction,
                    customer_data.get("tier", "standard")
                )
            )

            # Cache result
            customer_cache.set(cache_key, context)
            logger.info("Customer context built", 
                       external_id=external_id,
                       tier=context.tier,
                       is_high_value=context.is_high_value)

            return context

        except Exception as e:
            logger.error("Failed to get customer context", 
                        external_id=external_id, 
                        error=str(e))
            raise

    def _get_customer_from_db(self, external_id: str) -> Optional[dict]:
        """Fetch customer data from PostgreSQL."""
        query = text("""
            SELECT customer_id, external_id, email, name, company, tier, lifetime_value
            FROM customers
            WHERE external_id = :external_id
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"external_id": external_id})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        return None

    def _get_recent_orders(self, customer_id: str, limit: int = 5) -> dict:
        """Fetch recent orders from PostgreSQL."""
        count_query = text("""
            SELECT COUNT(*) as total FROM orders WHERE customer_id = :customer_id
        """)

        orders_query = text("""
            SELECT order_id, order_number, status, total_amount, order_date
            FROM orders
            WHERE customer_id = :customer_id
            ORDER BY order_date DESC
            LIMIT :limit
        """)

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
                ExpressionAttributeValues={
                    ":cid": customer_id,
                    ":cutoff": cutoff
                },
                ScanIndexForward=False,
                Limit=20
            )

            items = response.get("Items", [])

            # Calculate average sentiment
            sentiments = [float(i.get("sentiment", 0)) for i in items if "sentiment" in i]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            # Get last interaction timestamp
            last_interaction = None
            if items:
                last_interaction = datetime.fromisoformat(items[0]["timestamp"])

            return {
                "interactions": items[:10],  # Return top 10
                "avg_sentiment": round(avg_sentiment, 2),
                "last_interaction": last_interaction
            }

        except Exception as e:
            logger.warning("Failed to fetch interactions", error=str(e))
            return {"interactions": [], "avg_sentiment": 0.0, "last_interaction": None}

    def _calculate_churn_risk(
        self, 
        avg_sentiment: float, 
        last_interaction: Optional[datetime],
        tier: str
    ) -> str:
        """Calculate churn risk based on engagement signals."""
        risk_score = 0

        # Sentiment factor
        if avg_sentiment < -0.3:
            risk_score += 3
        elif avg_sentiment < 0:
            risk_score += 1

        # Recency factor
        if last_interaction:
            days_since = (datetime.utcnow() - last_interaction).days
            if days_since > 60:
                risk_score += 3
            elif days_since > 30:
                risk_score += 1
        else:
            risk_score += 2

        # Tier factor (enterprise customers get more attention)
        if tier == "enterprise" and risk_score > 0:
            risk_score += 1

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        return "low"
```

---

### 5.3 Cache Service (Cost Optimization)

**File:** `src/utils/cache_service.py`

```python
"""
In-Memory LRU Cache Service

Lightweight caching layer to reduce external calls.
Survives across warm Lambda invocations.
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check TTL
            if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl_seconds):
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, datetime.utcnow())

            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }
```

---

## 6. CDK INFRASTRUCTURE

### 6.1 Main Stack

**File:** `infrastructure/main_stack.py`

```python
"""
Main CDK Stack for AI Customer Support Platform

Deploys all Phase 1 infrastructure:
- Bedrock Knowledge Base with S3 data source
- RDS PostgreSQL for customer data
- DynamoDB for interaction logs
- API Gateway + Lambda for ticket API
- EventBridge for document sync automation
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    Tags,
    CfnOutput,
)
from constructs import Construct

from infrastructure.constructs.knowledge_base import KnowledgeBaseConstruct
from infrastructure.constructs.data_layer import DataLayerConstruct
from infrastructure.constructs.api_layer import ApiLayerConstruct
from infrastructure.constructs.event_pipeline import EventPipelineConstruct
from infrastructure.config.settings import Settings


class AISupportStack(Stack):
    """Main stack for AI Customer Support Platform."""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        settings: Settings,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Apply tags to all resources
        Tags.of(self).add("Project", "ai-customer-support")
        Tags.of(self).add("Environment", settings.environment)
        Tags.of(self).add("CostCenter", "support-automation")
        Tags.of(self).add("ManagedBy", "cdk")

        # 1. Knowledge Base Infrastructure
        kb_construct = KnowledgeBaseConstruct(
            self, "KnowledgeBase",
            environment=settings.environment,
            embedding_model_id=settings.embedding_model_id,
            chunking_max_tokens=settings.chunking_max_tokens,
            chunking_overlap_percentage=settings.chunking_overlap_percentage,
        )

        # 2. Data Layer (RDS + DynamoDB)
        data_construct = DataLayerConstruct(
            self, "DataLayer",
            environment=settings.environment,
            vpc=kb_construct.vpc,  # Share VPC
            db_instance_class=settings.db_instance_class,
        )

        # 3. API Layer (API Gateway + Lambda)
        api_construct = ApiLayerConstruct(
            self, "ApiLayer",
            environment=settings.environment,
            vpc=kb_construct.vpc,
            knowledge_base_id=kb_construct.knowledge_base.attr_knowledge_base_id,
            db_secret_arn=data_construct.db_secret.secret_arn,
            interactions_table_name=data_construct.interactions_table.table_name,
            model_id=settings.model_id,
        )

        # 4. Event Pipeline (S3 → EventBridge → Lambda → KB Sync)
        event_construct = EventPipelineConstruct(
            self, "EventPipeline",
            environment=settings.environment,
            documents_bucket=kb_construct.documents_bucket,
            knowledge_base_id=kb_construct.knowledge_base.attr_knowledge_base_id,
            data_source_id=kb_construct.data_source.attr_data_source_id,
        )

        # Grant permissions
        kb_construct.documents_bucket.grant_read(api_construct.main_lambda)
        data_construct.db_secret.grant_read(api_construct.main_lambda)
        data_construct.interactions_table.grant_read_write_data(api_construct.main_lambda)

        # Outputs
        CfnOutput(self, "ApiEndpoint", value=api_construct.api.url or "")
        CfnOutput(self, "KnowledgeBaseId", value=kb_construct.knowledge_base.attr_knowledge_base_id)
        CfnOutput(self, "DocumentsBucket", value=kb_construct.documents_bucket.bucket_name)
        CfnOutput(self, "InteractionsTable", value=data_construct.interactions_table.table_name)
```

---

### 6.2 Settings Configuration

**File:** `infrastructure/config/settings.py`

```python
"""
Environment-specific configuration settings.

Cost-optimized defaults for development/testing.
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class Settings:
    """Application settings with cost-optimized defaults."""

    # Environment
    environment: str = "dev"
    aws_region: str = "eu-west-2"

    # Bedrock Configuration
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"  # Cost-optimized
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # Knowledge Base Chunking
    chunking_max_tokens: int = 512
    chunking_overlap_percentage: int = 10

    # Database Configuration (Cost-optimized)
    db_instance_class: str = "db.t3.micro"  # Free tier eligible
    db_allocated_storage: int = 20  # Minimum GB

    # Lambda Configuration
    lambda_memory_mb: int = 512
    lambda_timeout_seconds: int = 30
    lambda_architecture: str = "ARM_64"  # 20% cheaper

    # Cache Configuration
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_max_size: int = 100

    @classmethod
    def from_environment(cls) -> "Settings":
        """Load settings from environment variables."""
        env = os.environ.get("ENVIRONMENT", "dev")

        # Production overrides
        if env == "prod":
            return cls(
                environment="prod",
                db_instance_class="db.t3.small",  # Upgrade for prod
                db_allocated_storage=50,
                lambda_memory_mb=1024,
                lambda_timeout_seconds=60,
            )

        return cls(environment=env)
```

---

## 7. DEPLOYMENT COMMANDS

```bash
# Initial setup
cd ai-support-platform
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT_ID/eu-west-2

# Synthesize CloudFormation template
cdk synth

# Deploy to dev environment
ENVIRONMENT=dev cdk deploy --require-approval never

# Deploy to production
ENVIRONMENT=prod cdk deploy --require-approval broadening

# Destroy stack (dev only)
ENVIRONMENT=dev cdk destroy --force
```

---

## 8. TESTING COMMANDS

```bash
# Run unit tests
pytest tests/unit -v --cov=src --cov-report=term-missing

# Run integration tests (requires deployed stack)
pytest tests/integration -v

# Test API endpoint locally
python scripts/test_local.py

# Seed knowledge base with sample documents
python scripts/seed_knowledge_base.py

# Seed customer data
python scripts/seed_customer_data.py
```

---

## 9. COST ESTIMATION (Phase 1)

| Service | Configuration | Est. Monthly Cost |
|---------|---------------|-------------------|
| **Bedrock KB** | 10K docs, 100K queries | $15-25 |
| **Bedrock Inference** | 500K tokens (Haiku) | $10-15 |
| **RDS PostgreSQL** | db.t3.micro, 20GB | $0 (Free Tier) |
| **DynamoDB** | On-demand, ~1M requests | $5-10 |
| **Lambda** | 100K invocations, 512MB | $5-10 |
| **API Gateway** | HTTP API, 1M requests | $1-2 |
| **S3** | 10GB storage | $0.25 |
| **CloudWatch** | Basic logging | $5-10 |
| **Secrets Manager** | 1 secret | $0.40 |
| **VPC NAT** | Minimal traffic | $30-45 |
| **Total** | | **$70-120/month** |

**Cost Optimization Tips:**
1. Use NAT Gateway only for production; use VPC endpoints for dev
2. Enable S3 Intelligent-Tiering for document storage
3. Set DynamoDB TTL to auto-expire old interaction logs
4. Use Bedrock Claude Haiku instead of Sonnet for 80% token savings
5. Implement aggressive caching to reduce API calls

---

## 10. ACCEPTANCE CRITERIA

### Phase 1 Completion Checklist

- [ ] **Knowledge Base**
  - [ ] S3 bucket created with lifecycle rules
  - [ ] Bedrock KB provisioned with Titan embeddings
  - [ ] Document ingestion pipeline working (S3 → KB)
  - [ ] Retrieval returning relevant results (>0.7 score)
  - [ ] Sync triggered automatically on document upload

- [ ] **Customer Context**
  - [ ] PostgreSQL database deployed with schema
  - [ ] DynamoDB table created for interactions
  - [ ] Customer 360 API returning complete context
  - [ ] Response time <200ms (warm Lambda)
  - [ ] In-memory cache working (cache hits logged)

- [ ] **Ticketing Integration**
  - [ ] API Gateway HTTP API deployed
  - [ ] POST /tickets endpoint accepting requests
  - [ ] GET /tickets/{id}/context returning suggestions
  - [ ] SQS queue processing tickets asynchronously
  - [ ] Dead-letter queue capturing failures

- [ ] **Infrastructure**
  - [ ] CDK deployment successful
  - [ ] All resources tagged correctly
  - [ ] CloudWatch logs streaming
  - [ ] IAM roles following least privilege
  - [ ] Secrets stored in Secrets Manager

- [ ] **Testing**
  - [ ] Unit tests passing (>80% coverage)
  - [ ] Integration tests passing
  - [ ] Sample data seeded successfully
  - [ ] API health check returning 200

---

## 11. NEXT PHASE PREVIEW (Phase 2)

Phase 2 will add:
- Ticket classification agent (Claude Haiku)
- Response generation with guardrails
- Agent feedback loop
- A/B testing framework

Estimated additional cost: +$50-100/month
