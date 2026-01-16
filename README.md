# AI-Assisted Customer Support & Helpdesk Automation

> Agentic, cost-optimized reference implementation.  
> AWS CDK (Python), Step Functions orchestration, Bedrock KB + Claude 3.5, RDS Postgres, DynamoDB.

## Quick start (Windows-friendly)
1) Create venv + install deps (PowerShell):
   - `py -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
2) Prereqs: install AWS CLI v2, Node.js 18+, `npm install -g aws-cdk`.
3) Bootstrap CDK (first time, use eu-west-2): `cdk bootstrap aws://YOUR_ACCOUNT/eu-west-2`
4) Deploy (dev):
   - `$env:ENVIRONMENT="dev"`
   - `$env:AWS_REGION="eu-west-2"`  # Default region
   - `cdk deploy --require-approval never`
5) Check outputs for `ApiEndpoint`, `KnowledgeBaseId`, `DocumentsBucket`.

## Architecture
- Single VPC (no NAT in dev) shared by RDS + Lambdas.
- S3 bucket feeds Bedrock Knowledge Base (OpenSearch Serverless backend).
- EventBridge rule triggers KB sync Lambda on S3 put/delete.
- HTTP API (v2) -> Lambda router -> handlers -> services.
- Step Functions state machine: classify → retrieve → generate (fallback to in-Lambda orchestration).
- PostgreSQL stores customer profiles/orders; DynamoDB stores interaction logs.
- In-memory LRU caches to minimize DB/KB calls.

### High-level diagram
```mermaid
flowchart LR
  subgraph Ingestion
    S3[KB Docs Bucket] --> EB[EventBridge Rule] --> Lsync[KB Sync Lambda] --> Bedrock[Bedrock KB]
  end
  subgraph APILayer
    Client --> APIgw[HTTP API] --> Lapi[Lambda Router]
    Lapi --> RDS[(Postgres)]
    Lapi --> DDB[(DynamoDB)]
    Lapi --> Bedrock
  end
  subgraph Agents
    APIgw --> SFN[Step Functions]
    SFN --> Lclass[Classify Lambda]
    SFN --> Lret[Retrieve Lambda]
    SFN --> Lgen[Generate Lambda]
  end
```

### Request flow
```mermaid
sequenceDiagram
  participant C as Client
  participant API as HTTP API
  participant L as Lambda Router
  participant SF as Step Functions
  participant DB as Postgres
  participant DD as DynamoDB
  participant KB as Bedrock KB

  C->>API: POST /tickets/auto-orchestrate
  API->>L: Proxy event
  L->>SF: start_sync_execution
  SF->>Lclass: classify
  SF->>Lret: retrieve context
  Lret->>KB: Vector search
  Lret->>DD: Similar tickets
  L->>DB: Structured lookups
  SF->>Lgen: generate drafts
  Lgen-->>SF: drafts + flags
  SF-->>L: orchestration result
  L-->>API: Response JSON + trace
  API-->>C: 200 OK
```

## Endpoints
- `POST /tickets` – ingest a ticket, return context + KB suggestions.
- `POST /tickets/classify` – classify ticket (category/priority/department/sentiment).
- `POST /tickets/context` – build retrieval context package from ticket + classification.
- `POST /tickets/respond` – generate drafts with guardrail flags; optional `use_sonnet`.
- `POST /tickets/auto-orchestrate` – run end-to-end Step Functions flow.
- `GET /tickets/{id}/context` – return customer 360.
- `POST /tickets/{id}/feedback` – stubbed acknowledgement.
- `GET /health` – health check.
- `POST /kb/sync` – manual KB ingestion trigger.

## Cost levers
- Dev VPC uses **no NAT** (S3 Gateway endpoint instead).
- ARM64 Lambdas, 512 MB memory by default.
- DynamoDB on-demand + TTL on interaction logs.
- Intelligent-Tiering hint for S3 uploads.
- Single Lambda router to maximize cache reuse and reduce cold starts.
- Haiku default for classification/generation; Sonnet opt-in via payload flag.
- Caching of classification + KB retrieval to avoid duplicate Bedrock calls.

## Testing
- Unit tests: `pytest tests/unit -v`
- Add DATABASE_URL/ AWS creds if you want live integration tests.

## Local run against real AWS (Windows, PowerShell)
- Prereqs: AWS CLI configured (`aws configure --profile dev`) and venv active.
- Set session env vars (example):
  - `$env:AWS_REGION="eu-west-2"`  # and optionally `$env:BEDROCK_REGION="eu-west-2"`
  - `$env:AWS_PROFILE="dev"`  # or set `AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY/SESSION_TOKEN`
  - `$env:DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname"`  
    # or `$env:DB_SECRET_ARN="arn:aws:secretsmanager:...:secret:your-secret"`
  - `$env:INTERACTIONS_TABLE="customer-interactions"`  # your DynamoDB table
  - `$env:KNOWLEDGE_BASE_ID="kb-xxxxxxxx"`  # optional; otherwise KB calls return empty suggestions
- Invoke handlers directly (no API Gateway) to hit real services:
  ```powershell
  python - <<'PY'
  import json, datetime
  from src.handlers import ticket_ingestion
  payload = {
      "ticket_id": "t-100",
      "external_ticket_id": "ext-100",
      "customer_external_id": "cust-ext-1",
      "subject": "Login issue",
      "description": "Reset password link fails",
      "channel": "email",
      "priority": "high",
      "created_at": datetime.datetime.utcnow().isoformat() + "Z",
  }
  event = {"body": json.dumps(payload)}
  print(ticket_ingestion.lambda_handler(event, None))
  PY
  ```
- To test customer context only:
  ```powershell
  python - <<'PY'
  from src.handlers import customer_context
  event = {"pathParameters": {"id": "cust-ext-1"}, "queryStringParameters": None}
  print(customer_context.lambda_handler(event, None))
  PY
  ```
- Tip: If you lack real AWS creds but want to avoid boto3 region errors, set dummy keys plus region:
  `$env:AWS_REGION="eu-west-2"; $env:AWS_ACCESS_KEY_ID="fake"; $env:AWS_SECRET_ACCESS_KEY="fake"`

## What to customize next
- Wire SQS for async ticket processing (Phase 2).
- Add DB migrations/seed scripts.
- Harden auth/throttling at API Gateway.
