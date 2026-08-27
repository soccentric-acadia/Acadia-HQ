#!/usr/bin/env bash
#
# e2e_device_enroll.sh — X5-012: end-to-end enrollment against the REAL
# gateway. Proves the full contract path from doc/hq-pairing-contract.md:
#
#   Rust device agent (Acadia-Configuration hq-agent, production run_agent
#   loop) → Python gateway (servicer/auth/DB) → device persisted as
#   pairing_state=authorized + online.
#
# Prerequisites: docker (disposable Postgres), python3 venv with the HQ deps
# (make install at the HQ root), cargo (builds the agent driver example).
#
# Usage:   make e2e-enroll        (from the HQ repo root)
#   or:    bash agent-gateway/tests/e2e_device_enroll.sh
#
# Exit codes: 0 = the device enrolled; 1 = any step failed.

set -uo pipefail
HQ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GW_ROOT="$HQ_ROOT/agent-gateway"
CFG_ROOT="${ACADIA_CONFIGURATION_DIR:-$HQ_ROOT/../Acadia-Configuration}"
PY="${HQ_ROOT}/.venv/bin/python"
PG_PORT="${E2E_PG_PORT:-55436}"
PG_CONTAINER="acadiahq-e2e-pg"
DB_URL="postgresql+asyncpg://acadiahq:acadiahq@localhost:${PG_PORT}/acadiahq_e2e"
TIMEOUT="${E2E_TIMEOUT_SECS:-30}"

fail() { echo "e2e: FAIL: $*" >&2; exit 1; }
cleanup() {
    [[ -n "${agent_pid:-}" ]] && kill "$agent_pid" 2>/dev/null
    [[ -n "${gateway_pid:-}" ]] && kill "$gateway_pid" 2>/dev/null
    docker rm -f "$PG_CONTAINER" >/dev/null 2>&1
}
trap cleanup EXIT

[ -d "$CFG_ROOT" ] || CFG_ROOT="$HQ_ROOT/../Acadia-Configuration"
[ -f "$CFG_ROOT/Cargo.toml" ] || fail "Acadia-Configuration not found at $CFG_ROOT"
[ -x "$PY" ] || fail "HQ venv missing (run: make -C $HQ_ROOT install)"
command -v docker >/dev/null || fail "docker required"
command -v cargo >/dev/null || fail "cargo required (rustup)"

# ── 1. Disposable Postgres ───────────────────────────────────────────────────
echo "== e2e: starting disposable postgres (:${PG_PORT}) =="
docker rm -f "$PG_CONTAINER" >/dev/null 2>&1
docker run -d --name "$PG_CONTAINER" \
    -e POSTGRES_DB=acadiahq_e2e -e POSTGRES_USER=acadiahq -e POSTGRES_PASSWORD=acadiahq \
    -p "${PG_PORT}:5432" postgres:16-alpine >/dev/null || fail "postgres container"
until docker exec "$PG_CONTAINER" pg_isready -U acadiahq >/dev/null 2>&1; do sleep 0.5; done

# ── 2. Schema + seed a pending device with a single-use pairing token ────────
export HQ_ROOT
echo "== e2e: provisioning device via the app models =="
export ACADIAHQ_TEST_DATABASE_URL="postgresql+asyncpg://acadiahq:acadiahq@localhost:${PG_PORT}/acadiahq_e2e"
"$PY" - <<'PYEOF'
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.environ["HQ_ROOT"], "agent-gateway"))
sys.path.insert(0, os.path.join(os.environ["HQ_ROOT"], "api"))

from app.db.base import Base, configure_for_tests, get_engine, get_session_factory
from app.models.device import Device
from app.models.device_credential import DeviceCredential
from app.models.enums import CredentialKind, PairingState
from app.models.tenant import Tenant
from app.services.credentials import generate_token, hash_token
from datetime import datetime, timedelta, UTC

async def main():
    configure_for_tests(os.environ["ACADIAHQ_TEST_DATABASE_URL"])
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.db.base import get_session_factory
    async with get_session_factory()() as session:
        tenant = Tenant(name="e2e-tenant")
        session.add(tenant); await session.flush()
        device = Device(tenant_id=tenant.id, name="e2e-device",
                        pairing_state=PairingState.pending)
        session.add(device); await session.flush()
        raw = generate_token()
        session.add(DeviceCredential(
            device_id=device.id, kind=CredentialKind.pairing,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=15)))
        await session.commit()
        # Hand the raw token to the shell via a file (never the command line).
        with open("/tmp/acadiahq_e2e_token", "w") as f:
            f.write(raw)
        print("e2e: device provisioned:", device.id)

asyncio.run(main())
PYEOF
[ -s /tmp/acadiahq_e2e_token ] || fail "token provisioning failed"

# ── 3. Start the real gateway ────────────────────────────────────────────────
if ss -tln 2>/dev/null | grep -q ":50515 "; then
    echo "e2e: FAIL: port 50515 already in use (stale gateway?) — kill it first" >&2
    exit 1
fi
echo "== e2e: starting the real agent-gateway on :50515 =="
ACADIAHQ_DATABASE_URL="postgresql+asyncpg://acadiahq:acadiahq@localhost:${PG_PORT}/acadiahq_e2e" \
ACADIAHQ_GATEWAY_GRPC_PORT="50515" \
    "$PY" -m gateway.server > /tmp/acadiahq_e2e_gateway.log 2>&1 &
gateway_pid=$!
for _ in $(seq 1 40); do
    grep -q "listening on" /tmp/acadiahq_e2e_gateway.log 2>/dev/null && break
    sleep 0.5
done
grep -q "listening on" /tmp/acadiahq_e2e_gateway.log || { cat /tmp/acadiahq_e2e_gateway.log; fail "gateway did not start"; }

# ── 4. Run the production Rust agent loop against it ─────────────────────────
# Fresh agent state each run: the pairing record persists by design, so a
# rerun with a new single-use token must start from a clean record.
rm -rf /tmp/acadiahq_e2e_agent
echo "== e2e: running the Rust device agent against the gateway =="
export AGENT_TOKEN AGENT_ENDPOINT AGENT_DATA_DIR AGENT_TIMEOUT_SECS
export AGENT_TOKEN="$(cat /tmp/acadiahq_e2e_token)"
AGENT_ENDPOINT="127.0.0.1:50515"
AGENT_DATA_DIR="/tmp/acadiahq_e2e_agent"
AGENT_TIMEOUT_SECS="$TIMEOUT"
( cd "$CFG_ROOT" && RUST_LOG=hq_agent=debug cargo run --quiet -p hq-agent --example e2e_enroll ) 2>/tmp/acadiahq_e2e_agent.log &
agent_pid=$!
agent_pid=$!

# ── 5. Assert HQ sees the device online + authorized ────────────────────────
enrolled=0
for _ in $(seq 1 $((TIMEOUT * 2))); do
    kill -0 "$agent_pid" 2>/dev/null || break
    result=$("$PY" - <<'PYEOF'
import asyncio, os, sys
from app.db.base import configure_for_tests, get_session_factory
from app.models.device import Device
from app.models.enums import PairingState

async def main():
    configure_for_tests(os.environ["ACADIAHQ_TEST_DATABASE_URL"])
    async with get_session_factory()() as session:
        d = (await session.execute(
            Device.__table__.select().where(
                Device.name == "e2e-device"))).mappings().first()
        if d is None:
            return "missing"
        return f"state={d['pairing_state']} online={d['online']}"
print(asyncio.run(main()))
PYEOF
    )
    if [[ "$result" == *"state=PairingState.authorized"* && "$result" == *"online=True"* ]]; then
        enrolled=1
        echo "e2e: HQ reports the device online + authorized ($result)"
        break
    fi
    sleep 0.5
done

kill "$agent_pid" "$gateway_pid" 2>/dev/null
wait "$agent_pid" 2>/dev/null

if [ "$enrolled" -eq 1 ]; then
    echo "== e2e: PASS — device enrolled against the real gateway =="
else
    echo "e2e: FAIL — device never became online+authorized (last: ${result:-none})" >&2
    tail -5 /tmp/acadiahq_e2e_gateway.log >&2 2>/dev/null
    echo "---- agent log ----" >&2
    tail -10 /tmp/acadiahq_e2e_agent.log >&2 2>/dev/null
    exit 1
fi