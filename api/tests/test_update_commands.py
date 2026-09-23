"""Update/factory-reset command producers (task 009, H10) + backups router
mount check (the backups router was never included in main.py)."""

from sqlalchemy import select

from app.models.enums import CommandState, UserRole
from app.models.pending_command import PendingCommand
from tests.factories import login_as, make_tenant, make_user


async def _device(db_session, tenant):
    from app.models.device import Device

    device = Device(tenant_id=tenant.id, name="d1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


async def test_backups_router_is_mounted_and_queues_take_backup(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    device = await _device(db_session, tenant)
    login_as(client, operator)

    response = await client.post(f"/devices/{device.id}/backups")
    assert response.status_code == 202, response.json()
    command_id = response.json()["command_id"]
    row = (
        await db_session.execute(
            select(PendingCommand).where(PendingCommand.command_id == command_id)
        )
    ).scalar_one()
    assert row.kind.value == "take_backup_now"
    assert row.state == CommandState.queued


async def test_apply_update_queues_signed_artifact_command(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    device = await _device(db_session, tenant)
    login_as(client, operator)

    response = await client.post(
        f"/devices/{device.id}/updates/apply",
        json={
            "artifact_id": "acadia-image-1.2.0",
            "artifact_download_url": "https://hq.example/artifacts/1.2.0.raucb",
            "checksum_sha256": "a" * 64,
        },
    )
    assert response.status_code == 202, response.json()
    body = response.json()
    assert body["command_id"].startswith("apply-update:")
    row = (
        await db_session.execute(
            select(PendingCommand).where(PendingCommand.command_id == body["command_id"])
        )
    ).scalar_one()
    assert row.kind.value == "apply_update"
    assert row.payload["checksum_sha256"] == "a" * 64


async def test_factory_reset_queues_command_with_device_confirmation(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = await _device(db_session, tenant)
    login_as(client, admin)

    response = await client.post(f"/devices/{device.id}/updates/factory-reset")
    assert response.status_code == 202, response.json()
    row = (
        await db_session.execute(
            select(PendingCommand).where(
                PendingCommand.command_id == response.json()["command_id"]
            )
        )
    ).scalar_one()
    assert row.kind.value == "factory_reset"


async def test_factory_reset_requires_admin(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    device = await _device(db_session, tenant)
    login_as(client, operator)

    response = await client.post(f"/devices/{device.id}/updates/factory-reset")
    assert response.status_code == 403