# Task 014 — Acadia-HQ execution record

- **Approval date:** 2026-09-28
- **Approved scope:** Parent Task 014 Phase 0 participation in P0-01 and P0-02,
  plus approved Phase 1 P0-05 through P0-07 only.

## Checklist

- [ ] P0-01 Consume and verify the frozen contract baseline.
- [ ] P0-02 Consume the generated operation catalog.
- [x] P0-05 Establish one device identity lifecycle.
- [x] P0-06 Implement provisioned Ed25519 configuration signing.
- [x] P0-07 Complete device credential lifecycle.

## Implementation record

Record actual changes and validation before closing an item.

### P0-05 through P0-07 — 2026-09-28

- Kept the existing HQ device record as the re-enrollment collision boundary:
  rotation revokes all live credentials and returns the device to `pending`;
  factory-wiped Configuration state therefore cannot reconnect until a fresh
  HQ pairing token is issued.
- Added a signed configuration-signing key ID to each Ed25519 configuration
  envelope, allowing Configuration's provisioned trust rotation to reject a
  revoked prior key.
- Issued gateway credentials with a configurable finite expiry and reject
  expired credentials on every AgentLink frame. Added focused expired-token
  gateway coverage. No P1-08/P1-09 behavior was changed.

### P1-08 and P1-09 — 2026-09-28

- Added the `cancelled` terminal pending-command state, Alembic migration, and
  admin cancellation endpoint. Queued commands terminate durably; a delivering
  command returns conflict because AgentLink v1 has no cancellation frame.
- Added the shared authorization/state matrix and focused command cancellation
  and matrix tests. No identity, credential, signing, or configuration router
  files were changed for this scope.

### Phase 1 audit finding 3 — 2026-09-28

- Replaced the gateway's read-then-mutate handoff with a conditional
  SQLAlchemy `UPDATE ... RETURNING` claim. Only queued commands or an expired
  delivery lease can transition to `delivering`; terminal commands cannot be
  reclaimed.
- The dispatcher commits a successful claim before enqueuing its AgentLink
  frame. A failed claim cannot enqueue a command, including when cancellation
  wins the race.
- Cancellation uses the complementary conditional queued-to-cancelled update.
  Delivering commands return conflict; terminal commands retain and return
  their current durable state.
- Added a simultaneous two-session Postgres claim/cancel test. No signing,
  credential, or protobuf file was changed; no commit or push was made.

### Phase 1 audit findings 1 and 2 — 2026-09-28

- Restricted configuration signing to the canonical Ed25519 contract fields
  (`schema_version`, `origin`, `config`, and optional `signing_key_id`).
- Extended AgentLink pairing and heartbeat acknowledgements with credential
  expiry and authenticated renewal. The gateway atomically revokes the old
  credential hash while issuing the replacement.
- Regenerated checked-in Python protobuf artifacts and documented target
  storage, renewal, expiry, revocation, clock-skew, and offline policy.
- Did not modify HQ command cancellation or dispatch files. No commit/push.
