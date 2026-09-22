# Task 009 — Acadia-HQ scope (leaf plan)
- **Status:** IMPLEMENTED — validated (see parent task validation.md)

Parent task: [`tasks/009-cross-repo-api-surface-audit/`](../../../../../tasks/009-cross-repo-api-surface-audit/plan.md)
in the Acadia parent repository.

## Role

agent-gateway is the server of `acadiahq.agent.AgentLink/Connect`; the API is
the producer of durable commands.

## Changes implemented

- `api/app/services/configuration.py` + `api/app/routers/configuration.py`:
  the `configuration.read/write` payload now matches the device contract —
  `schema_version`/`origin:"hq"`/`config` fields (task 009, H5), status
  `contract_v1_device_integrated`; transitional HMAC-SHA256 signature kept
  and documented (Ed25519 is the target).
- `api/app/services/operation_catalog.py` + `api/app/routers/devices.py`:
  integration status strings updated (contract now implemented on device).
- `api/app/routers/updates.py` (new): `POST /devices/{id}/updates/apply`
  (`apply_update` producer) and `POST /devices/{id}/updates/factory-reset`
  (`factory_reset` producer, admin-only) — finding H10.
- `api/app/main.py`: mounted `backups.router` (previously **never included**
  — `POST /devices/{id}/backups` did not exist) and the new updates router.
- `agent-gateway/gateway/servicer.py`:
  - `factory_reset` dispatch carries `required_confirmation="FACTORY-RESET"`
    (the device gate, finding H4);
  - commands now carry explicit `actor="hq"` and a device `deadline_ms`
    (finding H9);
  - `HeartbeatAck` advertises the new `device_heartbeat_interval_s` instead
    of the stale-sweep interval (finding H8).
- `agent-gateway/gateway/config.py`: `device_heartbeat_interval_s`,
  `command_deadline_ms`.
- Tests: `test_update_commands.py` (4, includes the backups-mount regression
  check); `test_frames.py` `json_payload` round-trip + failure-error tests;
  `test_phase3.py` configuration envelope assertions updated (and the known
  UUID-PK lookup debt fixed in the tests this task touches).

## Validation

- API pytest: 45 passed, 1 skipped; 1 pre-existing failure
  (`test_device_health_explains_offline_state`, verified failing on the clean
  tree too).
- Gateway pytest: 17 passed; 2 pre-existing failures
  (`test_duplicate_command_ack_is_terminal_and_does_not_retry`,
  `test_heartbeat_with_valid_credential_marks_device_online`), verified on
  the clean tree and already recorded in the parent `improvements.md`.