
## Phase 2 Implementation Spec — Generative AI & Agent Orchestration

This document is the actionable spec for Cursor to implement Phase 2.

### Objectives
- Deliver AI-assisted classification, retrieval, response generation, and routing for support tickets.
- Meet latency targets: classify <2s, retrieve <1s, generate drafts <3s batch.
- Enforce guardrails to block hallucinations, PII leakage, unsafe or off-brand responses.

### In Scope
- Ticket classification agent (Bedrock Agents) with category, priority, department, sentiment.
- Knowledge retrieval pipeline (Bedrock RAG + vector store + structured lookups + similar tickets).
- Response generation agent (Bedrock + Guardrails) producing drafts and citations.
- Orchestration via Lambda + Step Functions with fallback paths and feedback loop.

### Out of Scope
- UI changes in Phase 2 (assume API-first).
- Data labeling or KB authoring; only consumption of existing KB.
- Billing/quotas management (monitoring only).

### Non-Functional Requirements
- Performance: classify <2s; retrieve <1s; generate drafts <3s batch; end-to-end P95 <6s.
- Availability: 99.5% for API paths introduced here.
- Security: never log PII; use Secrets Manager for creds; apply least-privilege IAM.
- Cost: prefer Claude 3.5 Haiku unless Sonnet is required for reasoning; use ARM64 Lambdas.
- Observability: Lambda Powertools logging/tracing/metrics; correlation IDs in all responses.

### Architecture (Serverless, AWS CDK Python, Python 3.12, ARM64)
- API Gateway HTTP API (v2) → Lambda handlers (thin) → service classes.
- Step Functions state machine for orchestration:
  - Task 1: classify ticket (Bedrock Agent).
  - Task 2: conditional retrieval (vector search + rerank + structured lookups).
  - Task 3: response generation with guardrails.
  - Task 4: feedback loop updates and optional rerank.
  - Fallback branches for low-confidence retrieval or guardrail failures.
- Data:
  - Vector store (e.g., OpenSearch/S3 embeddings) for KB.
  - DynamoDB table for similar tickets, keyed by category + sentiment.
  - S3 for prompt templates and cached context packages (Intelligent-Tiering).

### Resource Conventions (must be applied)
- Lambda: ARM64, 512MB default, 30s timeout, Powertools enabled, layers for shared deps.
- IAM: least-privilege per function; scoped Bedrock, DynamoDB, S3, Step Functions.
- Tags: Project, Environment, CostCenter on all resources.
- Removal policy: DESTROY for dev; RETAIN for prod databases.

### Components and Contracts
1) Ticket Classification Agent
- Input: {title, description, customer_history, priority_hints?, channel?}.
- Output: {category (15–20 set), priority (Critical/High/Medium/Low), department, sentiment,
  confidence, reasoning_snippet}.
- Model: Claude 3.5 Sonnet for multi-factor reasoning.
- Validation: Pydantic models; reject empty title/description; enforce category enum.

2) Knowledge Retrieval Agent
- Input: ticket payload + category + priority + sentiment.
- Steps:
  - Vector search top-3; rerank with cross-encoder; include score.
  - Structured lookups: customer account rules, recent orders, SLAs.
  - Similar tickets: DynamoDB query by category + sentiment + resolution.
- Output: context_package = [{source_id, excerpt, score, citation_uri, type}], plus
  aggregate confidence.
- Metrics: RAGAS context precision/recall; log to metrics namespace.

3) Response Generation Agent
- Input: ticket + context_package + customer profile + brand guidelines.
- Process:
  - Generate 2–3 drafts; tone professional/empathetic/solution-focused.
  - Enforce guardrails: hallucination checks vs provided context; block PII/off-brand/
    unsafe content/overpromises.
- Output:
  - primary_draft, alternative_draft (e.g., escalation), suggested_next_steps,
  - confidence score, evidence citations, safety flags.
- Models: default Haiku; allow override to Sonnet for complex tickets (config flag).

4) Agentic Routing & Orchestration
- Step Functions flow:
  - classify → route → retrieve (if category requires KB) → generate → feedback stage.
  - Fallback: if retrieval confidence <0.6, escalate to L2 queue and return escalation draft.
  - If guardrails fail, return safe fallback template and flag for human review.
- Outputs: structured response payload with correlation_id, state trace, and timing data.

### API Surface (HTTP API stubs)
- POST /tickets/classify → returns classification payload.
- POST /tickets/context → runs retrieval given ticket + classification.
- POST /tickets/respond → returns drafts; optional `use_sonnet` flag.
- POST /tickets/auto-orchestrate → runs Step Functions state machine end-to-end.
- All responses: {correlation_id, data, timings_ms, warnings?, errors?}.

### Data Models (Pydantic v2 examples)
- TicketInput: title, description, customer_id, priority_hints?, channel?, locale?.
- ClassificationResult: category (enum), priority (enum), department, sentiment, confidence.
- RetrievalContextItem: source_id, excerpt, citation_uri, score, type (kb|order|ticket).
- ResponseDraft: text, citations[], confidence, safety_flags[].
- OrchestrationResult: classification, context_package, drafts[], next_actions[], trace.

### Error Handling
- Use custom exceptions in `src/utils/error_handling.py`.
- Log with context (ticket id, correlation_id) via Powertools, then re-raise.
- Return structured error with machine-readable code and human message; never include PII.

### Testing Requirements
- Unit tests for all service classes (pytest + pytest-asyncio).
- Moto for AWS mocks; snapshot tests for prompts where stable.
- Integration tests for orchestration happy path, low-confidence fallback, guardrail failure.
- Coverage >80% for `src/`.

### Observability and Metrics
- Powertools tracing on all handlers; capture Bedrock latency; Step Functions task timings.
- Metrics: classify_latency, retrieve_latency, generate_latency, end_to_end_latency_p95,
  ragas_precision, ragas_recall, guardrail_block_count, fallback_rate.

### Deployment and Config
- CDK stacks in Python; use L2 constructs where available.
- Config via environment variables; no secrets in code; Secrets Manager for DB creds.
- Feature flags: `USE_SONNET_FOR_COMPLEX`, `RETRIEVAL_CONFIDENCE_THRESHOLD`, `MAX_DRAFTS`.

### Acceptance Criteria
- API endpoints deployed in dev with working flows per contracts above.
- P95 latency targets met in load test with 50 RPS synthetic tickets.
- Guardrails block unsafe/PII cases in test suite; fallback path returns safe template.
- Logs contain correlation_id and timings; dashboards show key metrics.
- Documentation: updated README and `docs/api_spec.yaml` to reflect endpoints and payloads.

### Open Questions
- Final category taxonomy (15–20): confirm with CX team.
- Source systems for structured lookups (orders, account rules) and their schemas.
- Escalation destinations and thresholds by environment.