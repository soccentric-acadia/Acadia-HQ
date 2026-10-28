"""T-P20: HQ command producers (power, OTA activation, services, log
bundles, device accounts, allowlisted spoke operations)."""

import pytest
from sqlalchemy import select

from app.models.enums import CommandKind, CommandState, UserRole
from app.models.pending_command import PendingCommand
from tests.factories import login_as, make_tenant, make_user


async def _device(db_session, tenant):
    from app.models.device import Device

    device = Device(tenant_id=tenant.id, name="d1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


async def _row(db_session, command_id):
    return (
        await db_session.execute(
            select(PendingCommand).where(PendingCommand.command_id == command_id)
        )
    ).scalar_one()


async def _setup(db_session, client, role=UserRole.admin):
    tenant = await make_tenant(db_session)
    user = await make_user(db_session, tenant, role)
    device = await _device(db_session, tenant)
    await login_as(client, user)
    return device


@pytest.mark.parametrize(
    "path,kind",
    [
        ("power/reboot", "reboot"),
        ("updates/reboot-to-apply", "reboot_to_apply"),
        ("updates/confirm", "confirm_update"),
        ("logs/request", "log_bundle_request"),
    ],
)
async def test_operator_commands_queue(client, db_session, path, kind):
    device = await _setup(db_session, client, UserRole.operator)
    r = await client.post(f"/devices/{device.id}/{path}")
    assert r.status_code == 202, r.text
    row = await _row(db_session, r.json()["command_id"])
    assert row.kind.value == kind
    assert row.state == CommandState.queued


@pytest.mark.parametrize(
    "path,word,kind",
    [
        ("power/shutdown", "SHUTDOWN", "shutdown"),
        ("updates/rollback", "ROLLBACK", "rollback_update"),
    ],
)
async def test_destructive_commands_need_admin_and_confirmation(
    client, db_session, path, word, kind
):
    device = await _setup(db_session, client, UserRole.admin)
    bad = await client.post(f"/devices/{device.id}/{path}", json={"confirmation": "yes"})
    assert bad.status_code == 400
    ok = await client.post(f"/devices/{device.id}/{path}", json={"confirmation": word})
    assert ok.status_code == 202, ok.text
    assert (await _row(db_session, ok.json()["command_id"])).kind.value == kind


async def test_destructive_commands_refuse_operator(client, db_session):
    device = await _setup(db_session, client, UserRole.operator)
    r = await client.post(f"/devices/{device.id}/power/shutdown", json={"confirmation": "SHUTDOWN"})
    assert r.status_code == 403


async def test_service_control_validates_action(client, db_session):
    device = await _setup(db_session, client, UserRole.operator)
    bad = await client.post(
        f"/devices/{device.id}/services/control", json={"unit": "sshd.service", "action": "mask"}
    )
    assert bad.status_code == 422
    ok = await client.post(
        f"/devices/{device.id}/services/control", json={"unit": "sshd.service", "action": "restart"}
    )
    assert ok.status_code == 202
    row = await _row(db_session, ok.json()["command_id"])
    assert row.payload == {"unit": "sshd.service", "action": "restart"}


async def test_users_create_keeps_password_out_of_audit(client, db_session):
    from app.models.audit_log import AuditLog

    device = await _setup(db_session, client, UserRole.admin)
    r = await client.post(
        f"/devices/{device.id}/users/command",
        json={
            "operation": "users.create",
            "username": "ops1",
            "role": "operator",
            "password": "password9",
        },
    )
    assert r.status_code == 202, r.text
    row = await _row(db_session, r.json()["command_id"])
    assert row.kind.value == "users_command"
    assert row.payload["operation"] == "users.create"
    audits = (await db_session.execute(select(AuditLog))).scalars().all()
    assert audits and all("password9" not in str(a.payload) for a in audits)


async def test_users_create_requires_password_and_role(client, db_session):
    device = await _setup(db_session, client, UserRole.admin)
    r = await client.post(
        f"/devices/{device.id}/users/command", json={"operation": "users.create", "username": "x1"}
    )
    assert r.status_code == 400


async def test_spoke_operations_are_allowlisted_and_role_gated(client, db_session):
    device = await _setup(db_session, client, UserRole.operator)
    ok = await client.post(
        f"/devices/{device.id}/operations", json={"daemon": "networkd", "operation": "status"}
    )
    assert ok.status_code == 202, ok.text
    row = await _row(db_session, ok.json()["command_id"])
    assert row.kind.value == "operation_run"
    forbidden = await client.post(
        f"/devices/{device.id}/operations", json={"daemon": "ota", "operation": "apply"}
    )
    assert forbidden.status_code == 403
    admin_only = await client.post(
        f"/devices/{device.id}/operations", json={"daemon": "networkd", "operation": "ssh-open"}
    )
    assert admin_only.status_code == 403


async def test_command_cancel_reports_claimed_and_terminal_states(client, db_session):
    device = await _setup(db_session, client)
    delivering = PendingCommand(
        device_id=device.id,
        command_id="cancel:delivering",
        kind=CommandKind.reboot,
        state=CommandState.delivering,
    )
    terminal = PendingCommand(
        device_id=device.id,
        command_id="cancel:terminal",
        kind=CommandKind.reboot,
        state=CommandState.succeeded,
    )
    db_session.add_all((delivering, terminal))
    await db_session.commit()

    claimed = await client.post(f"/devices/{device.id}/commands/{delivering.command_id}/cancel")
    assert claimed.status_code == 409

    completed = await client.post(f"/devices/{device.id}/commands/{terminal.command_id}/cancel")
    assert completed.status_code == 200
    assert completed.json() == {"command_id": terminal.command_id, "state": "succeeded"}


async def test_queued_command_cancellation_is_terminal_and_idempotent(client, db_session):
    device = await _setup(db_session, client)
    command = PendingCommand(
        device_id=device.id,
        command_id="cancel:queued",
        kind=CommandKind.reboot,
        state=CommandState.queued,
    )
    db_session.add(command)
    await db_session.commit()

    first = await client.post(f"/devices/{device.id}/commands/{command.command_id}/cancel")
    second = await client.post(f"/devices/{device.id}/commands/{command.command_id}/cancel")

    assert first.json() == {"command_id": command.command_id, "state": "cancelled"}
    assert second.json() == first.json()
    await db_session.refresh(command)
    assert command.completed_at is not None
