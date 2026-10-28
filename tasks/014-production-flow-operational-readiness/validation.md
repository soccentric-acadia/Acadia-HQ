# Task 014 — Acadia-HQ Phase 0 validation

- `api/.venv/bin/python -m pytest -q tests/test_operation_discovery.py` —
  passed, 4 tests. The run emitted one third-party Authlib deprecation warning.

The test verifies the HQ-vendored Instrumentation catalog matches the
production contract lock and every advertised operation remains deliverable.

## Phase 1 P0-05 through P0-07

- `python -m py_compile agent-gateway/gateway/auth.py api/app/config.py
  api/app/services/configuration.py api/app/routers/configuration.py` —
  passed.
- `git diff --check` — passed.
- `pytest -q agent-gateway/tests/test_pairing.py` and
  `api/tests/test_pairing_tokens.py` — blocked before collection because the
  selected local Python environment does not contain `pytest-asyncio`.
  No environment/dependency change was made.

Focused gateway coverage for expired device credentials was added but awaits
execution in the repository's configured test environment.

## HQ configuration queue regression — 2026-09-28

- Corrected the configuration queue envelope construction: `signing_key_id`
  remains in the already-signed `unsigned_payload`, eliminating the
  uninitialized `payload` self-reference.
- `.venv/bin/python -m pytest -q api/tests/test_phase3.py
  api/tests/test_pairing_tokens.py` — passed, **14/14**. One third-party
  Authlib deprecation warning was emitted.
- `.venv/bin/python -m py_compile api/app/routers/configuration.py` and
  `git diff --check` — passed.

## Phase 1 P1-08 and P1-09

- Added focused cancellation and authorization-matrix tests.
- Focused API/gateway pytest collection remains blocked because the selected
  environment lacks `pytest-asyncio`; no dependency/environment change was
  made. `git diff --check` passed.

## Phase 1 audit finding 3 — HQ claim/cancel atomicity — 2026-09-28

- `.venv/bin/python -m pytest -q api/tests/test_device_commands.py
  --disable-warnings --maxfail=1` — passed, **13/13** (one third-party
  warning). Queued cancellation is terminal/idempotent; delivering commands
  report conflict and completed commands remain unchanged.
- `.venv/bin/python -m pytest -q agent-gateway/tests/test_frames.py -k
  claim_cancel_race --disable-warnings --maxfail=1` — passed, **1/1** (11
  deselected). Separate Postgres sessions race claim and cancellation; exactly
  one conditional transition wins.
- `.venv/bin/python -m ruff check api/app/services/commands.py
  api/app/routers/devices.py api/tests/test_device_commands.py
  agent-gateway/gateway/servicer.py agent-gateway/tests/test_frames.py` —
  passed. `git diff --check` — passed.
- Full `agent-gateway/tests/test_frames.py` was attempted and failed before
  command dispatch at the existing credential-renewal/protobuf mismatch:
  generated `HeartbeatAck` has no `renewed_credential_token` field. That is
  outside finding 3, and no signing, credential, or protobuf files were
  modified.

## Phase 1 audit findings 1 and 2 — 2026-09-28

- `.venv/bin/python -m pytest -q agent-gateway/tests/test_pairing.py` —
  passed, **11/11**. Includes expiry issuance/rejection, renewal, and
  revocation coverage.
- `.venv/bin/python -m pytest -q
  api/tests/test_phase3.py::test_configuration_write_requires_operator_and_queues_signed_values`
  — passed, **1/1**; one Authlib deprecation warning only. The test uses the
  generated Ed25519 test key to verify the canonical field set and rejects
  signing-key-ID substitution.
- `.venv/bin/python -m py_compile agent-gateway/gateway/auth.py
  agent-gateway/gateway/servicer.py api/app/services/configuration.py` and
  `git diff --check` — passed.
