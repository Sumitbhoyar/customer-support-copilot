# Unified Architecture Overview

Single view of the platform across ingestion, knowledge, and agentic orchestration. Cost levers stay on by default (ARM64, no NAT in dev, Haiku-first).

## Core components
- **HTTP API (v2)** → **Lambda router** (thin) → handlers → services.
- **Step Functions (Express)**: classify → retrieve → generate drafts (fallback to in-Lambda orchestration when SFN ARN absent).
- **Bedrock Knowledge Base**: OpenSearch Serverless + Titan embeddings; S3 data source with lifecycle to Intelligent-Tiering.
- **Bedrock Models**: Claude 3.5 Haiku default; Sonnet opt-in per request; Titan embeddings for KB.
- **Data stores**: RDS Postgres (profiles/orders), DynamoDB (interaction logs, similar tickets placeholder).
- **Sync pipeline**: S3 put/delete → EventBridge → KB sync Lambda → Bedrock ingestion job.
- **Caching**: in-memory LRU for customer context, classification, KB retrieval.

## Infra diagram (runtime + ingestion)
```mermaid
graph TB
  subgraph VPC
    API[HTTP API] --> L[Lambda Router]
    L --> RDS[(Postgres)]
    L --> DDB[(DynamoDB)]
    L --> Bedrock[Bedrock KB]
    L --> SFN[Step Functions Express<br/>classify -> retrieve -> generate]
    SFN --> Lclass[Classify Lambda]
    SFN --> Lret[Retrieve Lambda]
    SFN --> Lgen[Generate Lambda]
  end

  Docs[S3 KB Bucket<br/>Intelligent-Tiering] --> EB[EventBridge Rule] --> Sync[KB Sync Lambda] --> Bedrock
  L --- Docs
```

## Bedrock Knowledge Base pipeline
```mermaid
flowchart LR
  U[Users / Ops] -- Upload / delete docs --> S3[KB Docs Bucket<br/>Private, versioned<br/>Lifecycle: Intelligent-Tiering]
  S3 -- S3 Event (Put/Delete) --> EB[EventBridge Rule]
  EB --> Lsync[KB Sync Lambda<br/>ARM64, 256 MB]
  Lsync -- start_ingestion_job --> BR[Bedrock KB Ingestion<br/>DataSourceId + KB Id]
  BR --> OSS[OpenSearch Serverless<br/>Managed vector store]

  subgraph Runtime
    API[HTTP API v2] --> Lapi[Lambda Router<br/>ARM64, 512 MB<br/>Shared cache]
    Lapi --> BRRT[Bedrock Agent Runtime<br/>Claude 3.5 Haiku]
    BRRT --> OSS
    Lapi -->|/kb/sync| Lsync
  end
```

## Agentic orchestration flow
```mermaid
stateDiagram-v2
    [*] --> Classify
    Classify --> Retrieve: success
    Retrieve --> Generate: context ok
    Retrieve --> Escalate: low confidence
    Generate --> Feedback
    Escalate --> Feedback
    Feedback --> [*]
```

**Control plane**
- API calls `/tickets/auto-orchestrate` → Lambda router → Step Functions `start_sync_execution` (Express for cost).
- If `STATE_MACHINE_ARN` absent (local/dev), Lambda orchestrates inline using the same services.

**Data plane**
- **Classify**: Haiku (Sonnet optional) with caching and heuristic fallback.
- **Retrieve**: vector search (KB) + structured lookups (customer orders/SLA) + similar tickets stub; cached where possible.
- **Generate**: Haiku default, Sonnet on demand; emits drafts + citations + safety flags; safe fallback text on failure.

## API flow (router + handlers)
```mermaid
flowchart TB
  subgraph Ingress
    Client["Client / Frontend"] --> API["HTTP API v2<br/>Routes:<br/>/health<br/>/tickets<br/>/tickets/classify<br/>/tickets/context<br/>/tickets/respond<br/>/tickets/auto-orchestrate<br/>/tickets/{id}/context<br/>/tickets/{id}/feedback<br/>/kb/sync"]
  end

  API --> Lmain["Lambda Router main.py<br/>ARM64 512 MB<br/>Shared caches"]

  subgraph Handlers
    Lmain --> Hhealth[health_check.py]
    Lmain --> Hingest[ticket_ingestion.py]
    Lmain --> Hclass[classification.py]
    Lmain --> Hret[retrieval.py]
    Lmain --> Hresp[response_generation.py]
    Lmain --> Horch[orchestration.py]
    Lmain --> Hcontext[customer_context.py]
    Lmain --> Hsync[kb_sync.py]
  end

  Hingest --> CustSvc["CustomerService<br/>cache + Postgres + DynamoDB"] -->|profile/orders| RDS[(Postgres)]
  CustSvc -->|interactions| DDB[(DynamoDB)]
  Hingest --> KBsvc["BedrockService<br/>retrieve suggestions"] --> BRRT["Bedrock Agent Runtime"]
  BRRT --> BR["Knowledge Base / OpenSearch Serverless"]

  Hclass --> BRRT
  Hret --> BRRT
  Hresp --> BRRT
  Horch --> SFN
```

## Context assembly & guardrails
```mermaid
flowchart LR
    subgraph Context
        KB[Bedrock KB vector search] --> Rerank[Rerank]
        Orders[Structured lookups orders + SLA] --> Pack[Context package]
        Tickets[Similar tickets DynamoDB] --> Pack
        Rerank --> Pack
    end
    Pack --> Drafts[Draft generation]
    Drafts --> Guardrails[Guardrail checks + safety flags]
    Guardrails --> Response[Drafts + citations + flags]
```

## Data considerations
- Postgres: minimal storage (20 GB) and single AZ in dev; Multi-AZ + retention in prod.
- DynamoDB: on-demand + TTL to auto-trim interaction logs; future similar-ticket query can reuse.
- S3: Intelligent-Tiering by default; versioned, private.

## Operational knobs
- `ENVIRONMENT=prod` toggles DB retention/deletion protection and NAT usage.
- Lambda memory/timeout tunable via `Settings`; default ARM64 512 MB, 30s.
- Model selection: Haiku default, Sonnet via payload `use_sonnet`. Keep model IDs current per AWS Bedrock release notes.
- Caches: `CACHE_TTL_SECONDS`, `CACHE_MAX_SIZE` envs (classification/retrieval).

## Agentic additions at a glance
- Step Functions Express orchestration (classify → retrieve → generate) with inline fallback when `STATE_MACHINE_ARN` is absent.
- Endpoints: `/tickets/classify`, `/tickets/context`, `/tickets/respond`, `/tickets/auto-orchestrate`.
- Guardrails and safety flags: `pii_detected`, `off_brand`, `unsafe_content`, `low_context_confidence`; safe fallback drafts on model errors.
- Cost posture reinforced: Haiku-first, Sonnet opt-in, cached Bedrock calls, no NAT in dev, DynamoDB on-demand + TTL, Intelligent-Tiering for S3.

## Lifecycle summary
- Ingest: `/tickets` stores/returns customer context and KB suggestions.
- Classify/Retrieve/Respond: dedicated endpoints plus `/tickets/auto-orchestrate` for end-to-end flow.
- Sync: S3 events + manual `/kb/sync` keep KB fresh.
- Observability: structured JSON logs with correlation IDs; Step Functions traces when enabled.
