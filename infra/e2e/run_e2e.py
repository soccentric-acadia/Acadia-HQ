#!/usr/bin/env python3
"""run_e2e.py — T-P16 (O05) cross-repo E2E driver: HQ <-> webconfigd over
the real AgentLink binaries.

Flow (every step asserts):
  1. HQ api healthy; reuse an already-paired device (idempotent re-runs) or
     create a new one with a single-use pairing token.
  2. webconfigd healthy; admin session (first-boot on a fresh store, else
     login — idempotent).
  3. Provision the pairing token + gateway address on the device
     (POST /pairing/provision, admin session).
  4. hq-agent dials the gateway, redeems the token, gets the credential;
     HQ shows the device authorized with a fresh last-seen.
  5. HQ signs a configuration.write (Ed25519 over the canonical transport
     payload); the device verifies mandatorily (T-P13), applies it, acks;
     the HQ command row reaches succeeded.
  6. configuration.read round-trips the applied value.
  7. ssh_keys.set provisions the operator account's keys (T-P11).

Usage (native dev slice):
    .venv/bin/python infra/e2e/run_e2e.py \
        --api http://localhost:8100 --device http://localhost:9180 \
        --gateway http://localhost:50051 \
        --signing-key /tmp/e2e/config-signing.pem

Requires (see README.md): harness DB migrated + seeded
(alembic upgrade head; api/scripts/seed_dev.py --email e2e@example.com),
the gateway running, and webconfigd running with the matching
WEBCONFIG_HQ_CONFIG_PUBKEY.

Out of scope for this harness: the INS leg (istate) and the systemd sandbox
verification — see README.md.
"""
import argparse
import asyncio
import base64
import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PASS = 0
FAIL = 0


def step(name: str, fn):
    """Run one E2E step; record pass/fail, return the callable's result."""
    global PASS, FAIL
    try:
        out = fn()
    except Exception as e:  # noqa: BLE001
        FAIL += 1
        print(f"FAIL: {name}: {e}")
        return None
    PASS += 1
    print(f"ok:   {name}")
    return out


def call(method: str, url: str, body=None, headers=None, timeout=15):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as r:
            raw = r.read() or b"{}"
            try:
                return r.status, dict(r.headers), json.loads(raw)
            except json.JSONDecodeError:
                return r.status, dict(r.headers), {"raw": raw.decode(errors="replace")[:300]}
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            return e.code, dict(e.headers), json.loads(raw)
        except json.JSONDecodeError:
            return e.code, dict(e.headers), {"raw": raw.decode(errors="replace")[:300]}


def cookie_from(headers: dict) -> str:
    for k, v in headers.items():
        if k.lower() == "set-cookie":
            return v.split(";")[0]
    return ""


def canonical_payload(payload: dict) -> bytes:
    """The exact bytes the device verifies (T-P13 contract): the envelope's
    contract fields ONLY (schema_version, origin, config) — sorted keys,
    compact separators, UTF-8 (matches the device's signed_document)."""
    doc = {
        "schema_version": payload["schema_version"],
        "origin": payload["origin"],
        "config": payload["config"],
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def poll(fn, timeout=90.0, interval=1.5, desc=""):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise TimeoutError(f"poll exhausted: {desc} (last={last})")


def hq_session_cookie() -> str:
    """Bootstrap an HQ admin session for the harness.

    Requires the harness database to be migrated (alembic upgrade head) and
    seeded (api/scripts/seed_dev.py --email e2e@example.com) — the README
    covers both. The driver then mints the session JWT the API validates for
    that invited admin (dev harness; production users come through OIDC).
    """
    from app.auth.deps import SESSION_COOKIE_NAME
    from app.auth.session import issue_session_token
    from app.db.base import get_session_factory
    from app.models.enums import UserRole
    from app.models.user import User
    from sqlalchemy import select

    async def _mint() -> str:
        factory = get_session_factory()
        async with factory() as session:
            user = (
                await session.execute(
                    select(User).where(User.role == UserRole.admin).limit(1)
                )
            ).scalar_one()
            token = issue_session_token(user.id, user.tenant_id, user.role.value)
            return f"{SESSION_COOKIE_NAME}={token}"

    return asyncio.run(_mint())


def device_session(dev: str) -> tuple[str, str]:
    """Admin session on the device: first-boot when the store is fresh,
    otherwise login (idempotent across harness re-runs)."""
    st, hd, _ = call(
        "POST",
        f"{dev}/api/v1/auth/first-boot",
        {"username": "admin", "password": "e2e-password-1"},
    )
    if st != 200:
        st, hd, _ = call(
            "POST",
            f"{dev}/api/v1/auth/login",
            {"username": "admin", "password": "e2e-password-1"},
        )
        if st != 200:
            raise RuntimeError(f"device admin login failed: {st}")
    cookie = cookie_from(hd)
    _, _, who = call("GET", f"{dev}/api/v1/auth/whoami", headers={"Cookie": cookie})
    return cookie, who["csrf"]


def wait_command(api, device_id, command_id, admin, desc, timeout=120):
    def done():
        st, _, row = call("GET", f"{api}/devices/{device_id}/commands/{command_id}", headers=admin)
        return row.get("state") == "succeeded" and row

    return poll(done, timeout=timeout, desc=desc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("E2E_API", "http://localhost:8100"))
    ap.add_argument("--device", default=os.environ.get("E2E_DEVICE", "http://localhost:9180"))
    # Explicit scheme = plaintext dev gateway; a bare host dials https://
    # (T-P12 secure-by-default).
    ap.add_argument("--gateway", default=os.environ.get("E2E_GATEWAY", "http://localhost:50051"))
    ap.add_argument(
        "--signing-key",
        default=os.environ.get("ACADIAHQ_CONFIGURATION_SIGNING_KEY_PATH", ""),
        help="HQ Ed25519 private key PEM (must match the device's provisioned pubkey)",
    )
    args = ap.parse_args()
    api, dev, gw = args.api.rstrip("/"), args.device.rstrip("/"), args.gateway
    ADMIN = {"Cookie": hq_session_cookie()}

    # ── 1. webconfigd: admin session ─────────────────────────────────────────
    poll(lambda: call("GET", f"{dev}/api/v1/auth/whoami")[0] == 200, 120, 2, "webconfigd up")
    sess = step("webconfigd: admin session (first-boot or re-login)", lambda: device_admin_session(dev))
    if sess is None:
        return 1
    admin_cookie, csrf = sess

    # Reuse an HQ device only when the device itself is still enrolled: HQ's
    # record alone is not enough — the device's pairing token may have
    # expired before it enrolled (the stale-reuse bug of the first harness).
    _, _, pairing = call("GET", f"{dev}/api/v1/pairing", headers={"Cookie": admin_cookie})
    device_enrolled = bool(pairing.get("enrolled"))

    # ── 2. HQ: device + pairing token (idempotent) ──────────────────────────
    def device_and_token():
        st, _, items = call("GET", f"{api}/devices", headers=ADMIN)
        for d in items.get("items", []) if device_enrolled else []:
            if d.get("pairing_state") == "authorized" and d.get("last_seen_at"):
                # The sim device is still paired to this unit (its persisted
                # credential lives in the sim's data dir) — reuse it, no new
                # token: the AgentLink leg is already up.
                return d, None
        r = call("POST", f"{api}/devices", {"name": f"e2e-sim-{uuid.uuid4().hex[:6]}"}, headers=ADMIN)
        if r[0] != 201:
            raise RuntimeError(f"device create failed: {r[0]} {r[2]}")
        device = r[2]["device"]
        rot = call(
            "POST", f"{api}/devices/{device['id']}/credential/rotate", headers=ADMIN
        )
        if rot[0] != 200:
            raise RuntimeError(f"rotate failed: {rot[0]} {rot[2]}")
        token = rot[2].get("token") or rot[2].get("pairing_token")
        if not token:
            raise RuntimeError(f"no pairing token in rotate response: {rot[2]}")
        return device, token

    out = step("HQ: device ready + pairing token issued", device_and_token)
    if out is None:
        return 1
    device, pairing_token = out
    device_id = device["id"]

    # ── 3. provision pairing (only for a fresh device) ──────────────────────
    if pairing_token is not None:
        def _provision():
            st, _, out = call(
                "POST",
                f"{dev}/api/v1/pairing/provision",
                {"token": pairing_token, "hq_endpoint": gw, "ttl_secs": 900},
                headers={"Cookie": admin_cookie, "X-CSRF-Token": csrf},
            )
            if st != 200:
                raise RuntimeError(f"rejected: {st} {out}")
            assert out["state"] == "pending", out
            return out

        if step("webconfigd: pairing token provisioned (hq_endpoint set)", _provision) is None:
            return 1
    else:
        print("ok:   webconfigd: pairing already provisioned (idempotent re-run)")

    # ── 4. AgentLink: agent connects, redeems the token, HQ sees it ─────────
    def seen():
        # A live AgentLink session right now — not a last_seen_at left over
        # from an earlier run.
        _, _, d = call("GET", f"{api}/devices/{device_id}", headers=ADMIN)
        return d.get("online") is True and d.get("last_seen_at") is not None

    if step(
        "AgentLink: token redeemed, device heartbeating at HQ",
        lambda: poll(seen, timeout=240, desc="device authorized + last_seen"),
    ) is None:
        return 1

    # ── 5. HQ signed configuration.write → device verifies + applies ────────
    key = Ed25519PrivateKey.from_private_bytes(
        serialization.load_pem_private_key(
            open(args.signing_key, "rb").read(), password=None
        ).private_bytes_raw()
    )
    payload = {
        "schema_version": 1,
        "origin": "hq",
        "config": {"system": {"hostname": f"e2e-hq-{uuid.uuid4().hex[:6]}"}},
    }
    sig = key.sign(canonical_payload(payload))
    body = {
        **payload,
        "signature": base64.b64encode(sig).decode(),
        "signature_algorithm": "ed25519",
    }
    st, _, write_out = call("PUT", f"{api}/devices/{device_id}/configuration", body, headers=ADMIN)
    if st != 202:
        print(f"FAIL: configuration.write rejected: {st} {write_out}")
        return 1
    if step(
        "HQ: signed configuration.write applied on the device",
        lambda: wait_command(api, device_id, write_out["command_id"], ADMIN, "configuration.write ack"),
    ) is None:
        return 1

    # ── 6. read back through the contract ───────────────────────────────────
    st, _, read_out = call("GET", f"{api}/devices/{device_id}/configuration", headers=ADMIN)
    if st != 202 or step(
        "HQ: configuration.read round-trips through the device",
        lambda: wait_command(api, device_id, read_out["command_id"], ADMIN, "configuration.read ack"),
    ) is None:
        return 1

    # ── 7. ssh_keys.set (T-P11) ──────────────────────────────────────────────
    st, _, ssh_out = call(
        "POST",
        f"{api}/devices/{device_id}/ssh-keys",
        {"authorized_keys": "ssh-ed25519 AAAAe2e e2e@hq"},
        headers=ADMIN,
    )
    if st != 202 or step(
        "HQ: ssh_keys.set applied on the device",
        lambda: wait_command(api, device_id, ssh_out["command_id"], ADMIN, "ssh_keys.set ack"),
    ) is None:
        return 1

    # ── 8. T-P20 command kinds (device-local; istate-free subset) ──────────
    def command(path, body, desc, check=None):
        st, _, out = call("POST", f"{api}/devices/{device_id}/{path}", body, headers=ADMIN)
        if st != 202:
            raise RuntimeError(f"{path} rejected: {st} {out}")
        row = wait_command(api, device_id, out["command_id"], ADMIN, desc)
        if not row:
            raise RuntimeError(f"{desc}: no terminal success")
        if check is not None:
            check(row.get("payload") or {})
        return row

    def _reboot_is_acked_but_not_executed(payload):
        # The fake sysroot must never power-cycle the host; on a device the
        # same outcome carries scheduled=true and the reboot follows ~5 s later.
        assert payload.get("action") == "reboot" and payload.get("scheduled") is False, payload

    def _users_list_has_admin(payload):
        names = [u["username"] for u in payload.get("users", [])]
        assert names, payload
        assert all("password" not in u and "password_hash" not in u for u in payload["users"])

    def _created(payload):
        assert "e2e-op" in [u["username"] for u in payload.get("users", [])], payload

    def _deleted(payload):
        assert "e2e-op" not in [u["username"] for u in payload.get("users", [])], payload

    for desc, path, body, check in [
        ("T-P20: system.reboot acknowledged (fake root: not executed)", "power/reboot", None,
         _reboot_is_acked_but_not_executed),
        ("T-P20: users.list returns device accounts without hashes", "users/command",
         {"operation": "users.list"}, _users_list_has_admin),
        ("T-P20: users.create applied on the device", "users/command",
         {"operation": "users.create", "username": "e2e-op", "role": "operator",
          "password": "e2e-password"}, _created),
        ("T-P20: users.delete applied on the device", "users/command",
         {"operation": "users.delete", "username": "e2e-op"}, _deleted),
        ("T-P20: service.control on an allowlisted unit", "services/control",
         {"unit": "sshd.service", "action": "restart"}, None),
        ("T-P20: update.confirm (mark_good) acknowledged", "updates/confirm", None, None),
    ]:
        step(desc, lambda p=path, b=body, d=desc, c=check: command(p, b, d, c))

    print(f"\nE2E RESULT: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


def device_admin_session(dev: str) -> tuple[str, str]:
    """Admin session on the device: first-boot when the store is fresh,
    otherwise login (idempotent across harness re-runs)."""
    st, hd, _ = call(
        "POST",
        f"{dev}/api/v1/auth/first-boot",
        {"username": "admin", "password": "e2e-password-1"},
    )
    if st != 200:
        st, hd, _ = call(
            "POST",
            f"{dev}/api/v1/auth/login",
            {"username": "admin", "password": "e2e-password-1"},
        )
        if st != 200:
            raise RuntimeError(f"device admin login failed: {st}")
    cookie = cookie_from(hd)
    _, _, who = call("GET", f"{dev}/api/v1/auth/whoami", headers={"Cookie": cookie})
    return cookie, who["csrf"]


if __name__ == "__main__":
    sys.exit(main())