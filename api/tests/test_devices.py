import pytest

from datetime import datetime, timedelta, UTC

from app.models.device import Device
from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_device_list_sorted_online_then_recent_then_name(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    now = datetime.now(UTC)

    day_ago = now - timedelta(days=1)
    minute_ago = now - timedelta(minutes=1)
    db_session.add_all(
        [
            Device(tenant_id=tenant.id, name="offline-old", online=False, last_seen_at=day_ago),
            Device(tenant_id=tenant.id, name="online-b", online=True, last_seen_at=minute_ago),
            Device(tenant_id=tenant.id, name="online-a", online=True, last_seen_at=now),
        ]
    )
    await db_session.commit()

    await login_as(client, admin)
    resp = await client.get("/devices")
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()["items"]]
    assert names == ["online-a", "online-b", "offline-old"]


async def test_create_device_writes_audit_log(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    await login_as(client, admin)
    resp = await client.post("/devices", json={"name": "unit-1"})
    assert resp.status_code == 201
    assert resp.json()["device"]["pairing_state"] == "pending"

    audit_resp = await client.get("/audit-log")
    actions = [row["action"] for row in audit_resp.json()["items"]]
    assert "device.create" in actions


async def test_device_name_search(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    db_session.add_all(
        [
            Device(tenant_id=tenant.id, name="jetson-lab-1"),
            Device(tenant_id=tenant.id, name="jetson-lab-2"),
            Device(tenant_id=tenant.id, name="other"),
        ]
    )
    await db_session.commit()

    await login_as(client, admin)
    resp = await client.get("/devices", params={"q": "jetson"})
    names = {d["name"] for d in resp.json()["items"]}
    assert names == {"jetson-lab-1", "jetson-lab-2"}


@pytest.mark.asyncio
async def test_ssh_keys_set_queues_command(client, db_session):
    """T-P11 (B05): POST /devices/{id}/ssh-keys queues a durable ssh_keys.set
    command with the authorized_keys payload, admin-gated."""
    from sqlalchemy import select

    from app.models.pending_command import PendingCommand

    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    await login_as(client, admin)
    resp = await client.post("/devices", json={"name": "ssh-device"})
    assert resp.status_code == 201, resp.text
    device_id = resp.json()["device"]["id"]

    r = await client.post(
        f"/devices/{device_id}/ssh-keys",
        json={"authorized_keys": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI op@laptop"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert body["command_id"].startswith("ssh_keys.set:")

    row = (
        await db_session.execute(
            select(PendingCommand).where(PendingCommand.command_id == body["command_id"])
        )
    ).scalar_one()
    assert row.kind.value == "ssh_keys_set"
    assert row.payload["authorized_keys"].startswith("ssh-ed25519 ")


@pytest.mark.asyncio
async def test_ssh_keys_set_validates_body(client, db_session):
    """Non-string keys are rejected before any command row."""
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    await login_as(client, admin)
    resp = await client.post("/devices", json={"name": "ssh-bad"})
    device_id = resp.json()["device"]["id"]

    r = await client.post(f"/devices/{device_id}/ssh-keys", json={"authorized_keys": 42})
    assert r.status_code == 400
