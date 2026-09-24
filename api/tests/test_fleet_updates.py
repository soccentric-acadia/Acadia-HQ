"""T-P21 (K09/K11/N06): artifact store, staged rollouts, device tags."""

import hashlib

from sqlalchemy import select

from app.models.enums import CommandKind, RolloutStatus, UserRole
from app.models.pending_command import PendingCommand
from app.models.update import UpdateRollout
from app.services import rollouts
from tests.factories import login_as, make_tenant, make_user

BUNDLE = b"acadia-swu-bundle-test-bytes" * 64
SHA = hashlib.sha256(BUNDLE).hexdigest()


async def _devices(db_session, tenant, n, tags=None):
    from app.models.device import Device

    out = []
    for i in range(n):
        d = Device(tenant_id=tenant.id, name=f"dev-{i:02d}", tags=list(tags or []))
        db_session.add(d)
        out.append(d)
    await db_session.commit()
    for d in out:
        await db_session.refresh(d)
    return out


async def _artifact(client, version="1.2.0", body=BUNDLE, sha=SHA):
    r = await client.post(
        "/updates/artifacts",
        json={"version": version, "target_board_rev": "rev-c", "checksum_sha256": sha},
    )
    assert r.status_code == 201, r.text
    art = r.json()
    up = await client.put(f"/updates/artifacts/{art['id']}/content", content=body)
    return art, up


async def _commands(db_session, kind):
    return list(
        (
            await db_session.execute(select(PendingCommand).where(PendingCommand.kind == kind))
        ).scalars()
    )


async def test_artifact_upload_verifies_sha256(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    login_as(client, admin)
    art, bad = await _artifact(client, version="9.9.9", body=b"tampered")
    assert bad.status_code == 422
    listed = (await client.get("/updates/artifacts")).json()["items"]
    assert listed[0]["uploaded_at"] is None
    art, ok = await _artifact(client, version="1.2.0")
    assert ok.status_code == 200, ok.text
    assert ok.json()["size_bytes"] == len(BUNDLE)
    again = await client.put(f"/updates/artifacts/{art['id']}/content", content=BUNDLE)
    assert again.status_code == 409


async def test_rollout_requires_uploaded_artifact(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    await _devices(db_session, tenant, 2)
    login_as(client, admin)
    art, _ = await _artifact(client, version="2.0.0", body=b"x", sha=SHA)  # mismatch
    r = await client.post("/updates/rollouts", json={"artifact_id": art["id"], "target": "all"})
    assert r.status_code == 400
    assert "uploaded" in r.json()["detail"]


async def test_canary_passes_then_remainder_queued_and_activated(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    devices = await _devices(db_session, tenant, 10)
    login_as(client, admin)
    art, _ = await _artifact(client)
    r = await client.post(
        "/updates/rollouts",
        json={"artifact_id": art["id"], "target": "all", "canary_percent": 20},
    )
    assert r.status_code == 201, r.text
    rollout = r.json()
    assert sum(d["wave"] == 0 for d in rollout["devices"]) == 2
    started = (await client.post(f"/updates/rollouts/{rollout['id']}/start")).json()
    assert started["status"] == "in_progress"
    applies = await _commands(db_session, CommandKind.apply_update)
    assert len(applies) == 2
    assert applies[0].payload["checksum_sha256"] == SHA
    assert applies[0].payload["artifact_download_url"].startswith("http")

    row = await db_session.get(UpdateRollout, rollout["id"])
    canary_ids = [d["device_id"] for d in rollout["devices"] if d["wave"] == 0]
    for device_id in canary_ids:
        await rollouts.record_device_result(db_session, row.id, device_id, True, None)
    await db_session.commit()
    assert len(await _commands(db_session, CommandKind.apply_update)) == 10
    assert len(await _commands(db_session, CommandKind.reboot_to_apply)) == 2

    for d in devices:
        if str(d.id) not in {str(c) for c in canary_ids}:
            await rollouts.record_device_result(db_session, row.id, d.id, True, None)
    await db_session.commit()
    final = (await client.get(f"/updates/rollouts/{rollout['id']}")).json()
    assert final["status"] == "completed"
    assert final["summary"]["succeeded"] == 10


async def test_canary_failure_halts_rollout(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    await _devices(db_session, tenant, 5)
    login_as(client, admin)
    art, _ = await _artifact(client)
    rollout = (
        await client.post(
            "/updates/rollouts",
            json={
                "artifact_id": art["id"],
                "target": "all",
                "canary_percent": 40,
                "halt_failure_percent": 0,
                "auto_activate": False,
            },
        )
    ).json()
    await client.post(f"/updates/rollouts/{rollout['id']}/start")
    row = await db_session.get(UpdateRollout, rollout["id"])
    canary = [d["device_id"] for d in rollout["devices"] if d["wave"] == 0]
    await rollouts.record_device_result(db_session, row.id, canary[0], False, "checksum mismatch")
    await rollouts.record_device_result(db_session, row.id, canary[1], True, None)
    await db_session.commit()
    await db_session.refresh(row)
    assert row.status == RolloutStatus.halted
    assert "canary failure rate" in row.halted_reason
    assert len(await _commands(db_session, CommandKind.apply_update)) == 2
    assert await _commands(db_session, CommandKind.reboot_to_apply) == []
    # Operator override resumes the remainder.
    resumed = (await client.post(f"/updates/rollouts/{rollout['id']}/resume")).json()
    assert resumed["status"] == "in_progress"
    assert len(await _commands(db_session, CommandKind.apply_update)) == 5


async def test_device_group_rollout_targets_tag(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    devices = await _devices(db_session, tenant, 3)
    login_as(client, admin)
    r = await client.put(f"/devices/{devices[0].id}/tags", json={"tags": ["canary", "lab"]})
    assert r.status_code == 200 and r.json()["tags"] == ["canary", "lab"]
    bad = await client.put(f"/devices/{devices[1].id}/tags", json={"tags": ["no spaces"]})
    assert bad.status_code == 400
    art, _ = await _artifact(client)
    rollout = (
        await client.post(
            "/updates/rollouts",
            json={"artifact_id": art["id"], "target": "device_group", "tag": "canary"},
        )
    ).json()
    assert [d["device_id"] for d in rollout["devices"]] == [str(devices[0].id)]


async def test_artifacts_are_tenant_scoped(client, db_session):
    t1 = await make_tenant(db_session)
    t2 = await make_tenant(db_session)
    a1 = await make_user(db_session, t1, UserRole.admin)
    a2 = await make_user(db_session, t2, UserRole.admin)
    await db_session.commit()
    login_as(client, a1)
    art, _ = await _artifact(client)
    login_as(client, a2)
    assert (await client.get("/updates/artifacts")).json()["items"] == []
    r = await client.put(f"/updates/artifacts/{art['id']}/content", content=BUNDLE)
    assert r.status_code == 404


async def test_operator_cannot_create_rollouts(client, db_session):
    tenant = await make_tenant(db_session)
    op = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()
    login_as(client, op)
    r = await client.post(
        "/updates/artifacts",
        json={"version": "1", "target_board_rev": "r", "checksum_sha256": SHA},
    )
    assert r.status_code == 403
