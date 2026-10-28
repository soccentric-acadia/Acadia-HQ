# Task 014 — Acadia-HQ scope

Parent plan: [Acadia Task 014](../../../../tasks/014-production-flow-operational-readiness/plan.md).

## Scope

HQ owns fleet enrollment, RBAC, command dispatch/result visibility, data persistence and UI, rollout control, and the cloud operational posture. Execute P0-01, P0-02, P0-05 through P2-13, P0-16 through P1-20, P1-22, P2-24 through P0-26 where they affect HQ.

## Interfaces and expected work

- Device credential/key lifecycle, RBAC/scopes, idempotent command state, gateway retry/ack behavior, and audit history.
- Telemetry/fault/log/backup/update ingestion with correlation, completion, retention, operator state, and alert handling.
- Production deployment, secret/TLS handling, backups/restores, migration rollback, load testing, web E2E, and runbooks.

## Local and cross-repository validation

Run API, gateway, and web tests; add real-binary compose coverage through hq-agent and istate. Exercise delivery failures, duplicate commands, credential revocation, data/upload failures, rollout failures, restore drills, and operator workflows.
