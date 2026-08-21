# Acadia HQ

Cloud fleet-management app for Acadia devices — view devices remotely, manage
pairing/authorization, and run fleet operations (telemetry, faults/alarms,
logs, OTA updates, backup/restore, provisioning, factory reset, disable,
location).

## Project Description

Acadia-HQ is the cloud fleet-management service for Acadia devices. Its repository is split into an API application, an agent gateway, web assets, infrastructure configuration, database migrations, and protocol/tooling directories. The API surface covers device management and fleet operations: pairing and authorization, tenant-aware access, RBAC, telemetry, faults and alarms, logs, OTA/update flows, provisioning, backup/restore, factory reset, disable operations, and location-oriented data. The agent gateway provides the device-facing connection boundary and frame/pairing lifecycle support. The web directory supplies the operator-facing client.

The code is evolving rather than a finished cloud product. API tests cover devices, alarms, telemetry, pairing tokens, OIDC, RBAC, tenant isolation, and phase-specific behavior; gateway tests cover frames, pairing, and stale-session sweeping. The web tree includes component/store tests for faults and alarms, utilities, and authentication state. Those files show implementation beyond the old planning label, but do not establish production deployment readiness, complete endpoint coverage, or live device interoperability.

Use the Makefiles and `pyproject.toml` files in `api/` and `agent-gateway/` for environment-specific commands. Migrations and infrastructure must be reviewed with the target database and deployment environment. Authentication, tenant boundaries, destructive operations, OTA delivery, and gateway reconnect behavior require manual verification.

HQ also sits above a stateful device fleet: an apparently successful API response does not by itself prove that a device received an operation, retained authorization, or reported the resulting state. Review queueing, retries, stale connections, auditability, and tenant scoping with a representative deployment. The existing tests are useful evidence for isolated contracts, while live gateway and web workflows remain acceptance work.

## Feature Matrix

| # | Name / Description | Implemented? | Test Coverage? | Manual Test |
|---:|---|---|---|---|
| 1 | API application and device routes | Implemented | `api/tests/test_devices.py` | [ ] Manual verification required |
| 2 | Pairing and authorization tokens | Implemented | Pairing API and gateway tests | [ ] Manual verification required |
| 3 | OIDC authentication | Implemented | `test_oidc.py` | [ ] Manual verification required |
| 4 | RBAC enforcement | Implemented | `test_rbac.py` | [ ] Manual verification required |
| 5 | Tenant isolation | Implemented | `test_tenant_isolation.py` | [ ] Manual verification required |
| 6 | Telemetry ingestion/query | Implemented | `test_telemetry_router.py` | [ ] Manual verification required |
| 7 | Faults and alarms | Implemented | `test_alarms_router.py` | [ ] Manual verification required |
| 8 | Gateway frames and stale sweep | Implemented | Gateway frame/stale-sweep tests | [ ] Manual verification required |
| 9 | OTA, backup, provisioning, reset, disable, location | Partial: scope documented; completion varies | Partial/unknown | [ ] Manual verification required |
| 10 | Web operator client | Partial: source and focused tests exist | Web tests present | [ ] Manual verification required |
| 11 | Migrations and infrastructure deployment | Implemented | Execution unknown | [ ] Manual verification required |

## Test Evidence

Run API and gateway commands defined by their local Makefiles/`pyproject.toml`; web tests are configured under `web/vitest.config.ts`.
