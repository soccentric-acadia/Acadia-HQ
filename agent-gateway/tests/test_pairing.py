import time

import grpc
import pytest

from app.models.enums import PairingState
from acadiahq.agent_pb2 import AgentFrame, Heartbeat, PairingHandshake
from tests.factories import (
    make_authorized_device_with_credential,
    make_pending_device_with_pairing_token,
    make_tenant,
)


async def _pair(stub, token: str):
    async def frames():
        yield AgentFrame(pairing_handshake=PairingHandshake(pairing_token=token))

    async for frame in stub.Connect(frames()):
        return frame
    return None


async def test_valid_pairing_token_issues_credential_and_authorizes_device(
    gateway_stub, db_session
):
    tenant = await make_tenant(db_session)
    device, token = await make_pending_device_with_pairing_token(db_session, tenant)

    response = await _pair(gateway_stub, token)

    assert response.pairing_result.success is True
    assert response.pairing_result.device_id == str(device.id)
    assert response.pairing_result.credential_token
    assert response.pairing_result.credential_expires_at_unix_ms > int(time.time() * 1000)

    await db_session.refresh(device)
    assert device.pairing_state == PairingState.authorized


async def test_invalid_pairing_token_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    await make_pending_device_with_pairing_token(db_session, tenant)

    response = await _pair(gateway_stub, "not-a-real-token")

    assert response.pairing_result.success is False


async def test_expired_pairing_token_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, token = await make_pending_device_with_pairing_token(db_session, tenant, expired=True)

    response = await _pair(gateway_stub, token)

    assert response.pairing_result.success is False
    await db_session.refresh(device)
    assert device.pairing_state == PairingState.pending


async def test_pairing_token_is_single_use(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    _, token = await make_pending_device_with_pairing_token(db_session, tenant)

    first = await _pair(gateway_stub, token)
    assert first.pairing_result.success is True

    second = await _pair(gateway_stub, token)
    assert second.pairing_result.success is False


async def test_heartbeat_with_valid_credential_marks_device_online(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
                agent_version="test",
            )
        )

    got_ack = False
    async for frame in gateway_stub.Connect(frames()):
        if frame.HasField("heartbeat_ack"):
            got_ack = True

    assert got_ack
    await db_session.refresh(device)
    assert device.last_seen_at is not None
    # The heartbeat marked the device online; closing the stream (the end of
    # this frame iterator) marks it offline again — both transitions are
    # audited. Asserting `online is True` after the stream closed tested the
    # pre-"stream_closed" semantics (HQ-019).
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    actions = [
        row.action
        for row in (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.target_device_id == device.id)
                .order_by(AuditLog.created_at)
            )
        ).scalars()
    ]
    assert actions[:1] == ["device.online"]
    assert actions[-1] == "device.offline"
    assert device.online is False


async def test_heartbeat_with_invalid_credential_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, _real_credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token="wrong-token",
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_expired_device_credential_is_rejected(gateway_stub, db_session):
    """Expired credentials fail closed even if the device has not reconnected."""
    from datetime import UTC, datetime, timedelta

    from app.models.device_credential import DeviceCredential

    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    await db_session.execute(
        DeviceCredential.__table__.update()
        .where(DeviceCredential.device_id == device.id)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_authenticated_heartbeat_renews_credential_before_expiry(
    gateway_stub, db_session
):
    """Renewal is delivered only after the current credential authenticates."""
    from sqlalchemy import select

    from app.models.device_credential import DeviceCredential
    from app.services.credentials import hash_token

    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    responses = [response async for response in gateway_stub.Connect(frames())]
    ack = next(response.heartbeat_ack for response in responses if response.HasField("heartbeat_ack"))
    assert ack.renewed_credential_token
    assert ack.renewed_credential_token != credential
    assert ack.credential_expires_at_unix_ms > int(time.time() * 1000)

    credentials = (
        await db_session.execute(
            select(DeviceCredential).where(DeviceCredential.device_id == device.id)
        )
    ).scalars().all()
    assert any(row.revoked_at is not None for row in credentials)
    assert any(
        row.revoked_at is None and row.token_hash == hash_token(ack.renewed_credential_token)
        for row in credentials
    )


async def test_disabled_device_heartbeat_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    device.pairing_state = PairingState.disabled
    await db_session.commit()

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_credential_revoked_midstream_ends_the_session(gateway_stub, db_session):
    """X5-005: the gateway validates the credential on EVERY frame, so a
    rotation/revocation takes effect immediately — the live session is torn
    down on the next frame instead of surviving until reconnect (contract
    doc/hq-pairing-contract.md §Enrollment/§Revocation)."""
    import asyncio
    from datetime import UTC, datetime

    from app.models.device_credential import DeviceCredential

    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    revocation_done = asyncio.Event()

    async def frames():
        # First heartbeat: valid, keeps the stream open.
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )
        # The gateway's HeartbeatAck arrives; the test revokes the credential
        # (simulating rotate_credential), then this second heartbeat must not
        # produce a response — the session must end.
        await revocation_done.wait()
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    responses = []
    async for response in gateway_stub.Connect(frames()):
        responses.append(response)
        assert response.HasField("heartbeat_ack"), "first frame must be acked"
        # Revoke exactly like the rotation endpoint does.
        now = datetime.now(UTC)
        await db_session.execute(
            DeviceCredential.__table__.update()
            .where(
                DeviceCredential.device_id == device.id,
                DeviceCredential.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        device.pairing_state = PairingState.pending
        await db_session.commit()
        revocation_done.set()

    # The stream must end after the revoked frame — no second response.
    assert len(responses) == 1, f"gateway leaked frames after revocation: {responses}"


async def test_revoked_credential_cannot_reconnect(gateway_stub, db_session):
    """X5-006 (device side): after a rotation revokes the old credential, a
    reconnect attempt with it fails UNAUTHENTICATED — the device must re-enroll
    with the fresh pairing token."""
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    # Rotation equivalent: revoke all credentials + park the device.
    from datetime import UTC, datetime

    from app.models.device_credential import DeviceCredential

    now = datetime.now(UTC)
    await db_session.execute(
        DeviceCredential.__table__.update()
        .where(
            DeviceCredential.device_id == device.id,
            DeviceCredential.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    device.pairing_state = PairingState.pending
    await db_session.commit()

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
