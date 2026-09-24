"""T-P23 (I04/I05): HQ alarm ack/clear reach the device; rule update/delete."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.pending_command import PendingCommand
from tests.factories import login_as, make_tenant, make_user


async def _setup(db_session, client, role=UserRole.operator):
    from app.models.device import Device
    from app.models.device_alarm import DeviceAlarm

    tenant = await make_tenant(db_session)
    user = await make_user(db_session, tenant, role)
    device = Device(tenant_id=tenant.id, name="d1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    alarm = DeviceAlarm(
        device_id=device.id, major_id=1, sub_section=4, fault_type=1, severity=2,
        alarm_code=0x01040102, triggered_at=datetime.now(UTC),
    )
    db_session.add(alarm)
    await db_session.commit()
    await db_session.refresh(alarm)
    await login_as(client, user)
    return device, alarm


async def _command(db_session, command_id):
    return (
        await db_session.execute(
            select(PendingCommand).where(PendingCommand.command_id == command_id)
        )
    ).scalar_one()


async def test_acknowledge_and_clear_propagate_to_the_alarms_spoke(client, db_session):
    device, alarm = await _setup(db_session, client)
    ack = await client.post(f"/devices/{device.id}/alarms/{alarm.id}/acknowledge")
    assert ack.status_code == 200, ack.text
    assert ack.json()["state"] == "acknowledged"
    cmd = await _command(db_session, ack.json()["device_command_id"])
    assert cmd.kind.value == "operation_run"
    assert cmd.payload == {"daemon": "alarms", "operation": "ack", "args": {"id": 0x01040102}}

    clear = await client.post(f"/devices/{device.id}/alarms/{alarm.id}/clear")
    assert clear.status_code == 200
    assert clear.json()["state"] == "resolved"
    cmd = await _command(db_session, clear.json()["device_command_id"])
    assert cmd.payload["operation"] == "clear"
    assert cmd.payload["args"]["id"] == 0x01040102
    assert cmd.payload["args"]["owner"].startswith("hq:")

    again = await client.post(f"/devices/{device.id}/alarms/{alarm.id}/acknowledge")
    assert again.status_code == 409


async def test_alarm_rule_update_and_delete(client, db_session):
    await _setup(db_session, client, UserRole.admin)
    created = await client.post(
        "/alarm-rules", json={"name": "cpu", "condition": {"metric": "cpu", "gt": 90}}
    )
    rule_id = created.json()["id"]
    patched = await client.patch(f"/alarm-rules/{rule_id}", json={"enabled": False})
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False
    assert patched.json()["name"] == "cpu"
    deleted = await client.delete(f"/alarm-rules/{rule_id}")
    assert deleted.status_code == 204
    assert (await client.get("/alarm-rules")).json() == []


async def test_alarm_rule_with_history_cannot_be_deleted(client, db_session):
    from app.models.alarm import Alarm

    device, _ = await _setup(db_session, client, UserRole.admin)
    rule_id = (
        await client.post("/alarm-rules", json={"name": "t", "condition": {}})
    ).json()["id"]
    db_session.add(
        Alarm(
            alarm_rule_id=rule_id, device_id=device.id,
            triggered_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    r = await client.delete(f"/alarm-rules/{rule_id}")
    assert r.status_code == 409
