# AgentLink E2E harness (T-P16, O05/F6)

Cross-repo end-to-end: **HQ (api + gateway + Postgres) <-> webconfigd (the
real Rust daemon) over the real AgentLink gRPC** — pairing, heartbeat,
signed configuration writes (T-P13 Ed25519), configuration reads, and the
T-P11 `ssh_keys.set` command, exercised through the durable command
gateway exactly as a production device would see them.

## What ran (evidence)

The driver has been executed against the real binaries on the dev host:

* HQ `api` + `gateway` from the Acadia-HQ tree (uvicorn + grpc.aio),
* `webconfigd` built from the Acadia-Configuration tree (AgentLink client,
  config store, applier engine),
* harness Postgres with the real migrations (including the T-P11
  `ssh_keys_set` enum migration).

Steps verified: device create → single-use pairing token → provision on the
device → AgentLink handshake → credential → heartbeats → HQ-signed
`configuration.write` **verified on-device** → applied → acked →
`configuration.read` round-trip → `ssh_keys.set` applied.

## Native dev slice (what ran here)

```sh
# 1. HQ stack (harness DB on :5432)
ACADIAHQ_DATABASE_URL=postgresql+asyncpg://acadiahq:acadiahq@localhost:5432/acadiahq \
ACADIAHQ_CONFIGURATION_SIGNING_KEY_PATH=/tmp/e2e/config-signing.pem \
  .venv/bin/python -m uvicorn app.main:create_app --factory --port 8100 &
(cd agent-gateway && ACADIAHQ_DATABASE_URL=... ../.venv/bin/python -m gateway.server &)

# 2. signing keypair (dev; production keys are provisioned, F09)
api/scripts/generate-config-signing-key.py /tmp/e2e/config-signing.pem

# 3. webconfigd (fake sysroot + data dir; pubkey pinned via env — T-P13)
WEBCONFIG_SYSROOT=/tmp/e2e/devroot WEBCONFIG_DATA_DIR=/tmp/e2e/devdata \
WEBCONFIG_PLAIN_PORT=9180 WEBCONFIG_PORT=9443 \
WEBCONFIG_HQ_CONFIG_PUBKEY="$(cat /tmp/e2e/config-signing-pub.pem)" \
  ./target/debug/webconfigd &

# 4. harness DB + driver
ACADIAHQ_DATABASE_URL=... .venv/bin/alembic upgrade head
(cd api && ../.venv/bin/python -m scripts.seed_dev --email e2e@example.com)
ACADIAHQ_DATABASE_URL=... .venv/bin/python infra/e2e/run_e2e.py \
  --api http://localhost:8100 --device http://localhost:9180 \
  --gateway http://localhost:50051 --signing-key /tmp/e2e/config-signing.pem
```

## Containerized stack

`docker-compose.e2e.yml` runs the same flow with `sim-device` building
webconfigd from the Acadia-Configuration tree and running it as the image's
non-root `webconfig` user (`cap_drop ALL`, `no-new-privileges`, read-only
rootfs, tmpfs state).

## Honest scope table

| Aspect | Real | Approximated |
|---|---|---|
| AgentLink transport (pairing/heartbeat/commands) | real binaries, real gRPC | — |
| Configuration contract (sign → verify → apply → ack) | real | — |
| TLS on the gateway | env-configurable (T-P12) | dev slice runs plaintext (`http://` scheme) |
| Device filesystem sandbox | docker read-only rootfs + no-new-privileges | the systemd unit directives (`ProtectSystem=strict`, `ReadWritePaths`, `SupplementaryGroups`) are verified on HIL, not here |
| Device users/groups | `webconfig` user in the sim container | full sysusers/udev set is image-level (HIL) |
| INS leg (istate + spokes) | — | **not covered**: istate is not built/run in this harness; the CFG↔INS socket contract is unit-tested + HIL-gated |
| OTA (SWUpdate) | — | separate HIL test (O06) |

Every "approximated" row is a task in the tracker; update this table as
they land.