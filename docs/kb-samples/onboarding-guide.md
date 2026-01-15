---
title: Onboarding checklist
product: Support Cloud
version: 1.0
---

# Who should use this
Admins setting up a new workspace and support agents joining the team.

# Admin setup (15–30 minutes)
1) Create teams/queues: Admin > Teams. Add escalation paths.
2) Connect channels: Admin > Channels. Add email, chat widget, and WhatsApp.
3) SSO & MFA: enable SSO (SAML/OIDC) and enforce MFA for agents.
4) SLAs: set response/resolution targets per priority.
5) Roles & permissions: grant least privilege; auditors get read-only.
6) KB sync: point the S3 bucket to Bedrock KB ingestion and trigger `/kb/sync`.

# Agent basics (10 minutes)
1) Log in and set your status (Available/Away).
2) Learn the triage view: priority, SLA badge, and sentiment.
3) Use reply templates for common responses; avoid freeform for PII.
4) Check the customer context panel for LTV, sentiment, and recent orders.
5) Suggest articles from KB search; link sources in replies.

# Go-live checklist
- Test ticket intake from each channel.
- Verify notifications (email/push) for new and escalated tickets.
- Run `/health` and `/tickets/{id}/context` smoke tests.
- Confirm billing contact and backup admin are set.
