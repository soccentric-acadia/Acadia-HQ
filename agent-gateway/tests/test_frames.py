import time

from sqlalchemy import select

from app.models.alarm import Alarm, AlarmRule
from app.models.enums import CommandKind, CommandState
from app.models.fault import Fault
from app.models.log_bundle import LogBundle
from app.models.pending_command import PendingCommand
from app.models.telemetry import TelemetrySample
from acadiahq.agent_pb2 import (
    AgentFrame,
    FaultEvent,
    Heartbeat,
    LogUploadRequest,
    TelemetryBatch,
    TelemetrySample as PbTelemetrySample,
)
from tests.factories import make_authorized_device_with_credential, make_tenant


def _hb(device_id: str, credential: str) -> Heartbeat:
    return Heartbeat(
        device_id=device_id, credential_token=credential, sent_at_unix_ms=int(time.time() * 1000)
    )


async def test_telemetry_batch_persists_samples(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            telemetry_batch=TelemetryBatch(
                samples=[
                    PbTelemetrySample(
                        metric="cpu_pct", value=55.5, recorded_at_unix_ms=int(time.time() * 1000)
                    )
                ]
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    stmt = select(TelemetrySample).where(TelemetrySample.device_id == device.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].metric == "cpu_pct"
    assert rows[0].value == 55.5


async def test_fault_event_raises_fault_and_triggers_matching_alarm_rule(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    db_session.add(
        AlarmRule(
            tenant_id=tenant.id,
            name="critical",
            condition={"kind": "fault_code", "severity": "critical"},
        )
    )
    await db_session.commit()

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP",
                severity=FaultEvent.CRITICAL,
                message="cpu too hot",
                kind=FaultEvent.RAISED,
                at_unix_ms=int(time.time() * 1000),
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    faults = (
        await db_session.execute(select(Fault).where(Fault.device_id == device.id))
    ).scalars().all()
    assert len(faults) == 1
    assert faults[0].code == "OVERTEMP"

    alarms = (
        await db_session.execute(select(Alarm).where(Alarm.device_id == device.id))
    ).scalars().all()
    assert len(alarms) == 1
    assert alarms[0].source_fault_id == faults[0].id


async def test_fault_clear_sets_cleared_at_on_open_fault(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP",
                severity=FaultEvent.WARN,
                kind=FaultEvent.RAISED,
                at_unix_ms=1_700_000_000_000,
            )
        )
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP", kind=FaultEvent.CLEARED, at_unix_ms=1_700_000_010_000
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    fault = (
        await db_session.execute(select(Fault).where(Fault.device_id == device.id))
    ).scalar_one()
    assert fault.cleared_at is not None


async def test_log_upload_request_returns_signed_url_and_creates_bundle(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            log_upload_request=LogUploadRequest(
                kind=LogUploadRequest.LOG_BUNDLE,
                time_range_start_unix_ms=1_700_000_000_000,
                time_range_end_unix_ms=1_700_000_060_000,
                size_bytes_estimate=2048,
            )
        )

    saw_signed_url = False
    async for frame in gateway_stub.Connect(frames()):
        if frame.HasField("signed_upload_url"):
            saw_signed_url = True
            assert frame.signed_upload_url.upload_url

    assert saw_signed_url
    bundles = (
        await db_session.execute(select(LogBundle).where(LogBundle.device_id == device.id))
    ).scalars().all()
    assert len(bundles) == 1
    assert bundles[0].size_bytes == 2048


async def test_fault_and_telemetry_are_ingested_while_command_is_in_flight(
    gateway_stub, db_session
):
    """The command stream must not block independent device observations."""
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    command = PendingCommand(
        device_id=device.id,
        command_id="backup:in-flight",
        kind=CommandKind.take_backup_now,
        state=CommandState.queued,
        correlation_id="corr-in-flight",
    )
    db_session.add(command)
    await db_session.commit()

    from acadiahq.agent_pb2 import CommandAck

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            telemetry_batch=TelemetryBatch(
                samples=[
                    PbTelemetrySample(
                        metric="cpu_pct",
                        value=91.0,
                        recorded_at_unix_ms=int(time.time() * 1000),
                    )
                ]
            )
        )
        yield AgentFrame(
            fault_event=FaultEvent(
                code="BACKUP_BUSY",
                severity=FaultEvent.WARN,
                message="backup still running",
                kind=FaultEvent.RAISED,
                at_unix_ms=int(time.time() * 1000),
            )
        )
        yield AgentFrame(
            command_ack=CommandAck(
                command_id=command.command_id,
                success=True,
                correlation_id=command.correlation_id,
                code="OK",
                operation="backup",
                daemon="configuration",
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    samples = (
        await db_session.execute(
            select(TelemetrySample).where(TelemetrySample.device_id == device.id)
        )
    ).scalars().all()
    faults = (
        await db_session.execute(select(Fault).where(Fault.device_id == device.id))
    ).scalars().all()
    await db_session.refresh(command)
    assert [(sample.metric, sample.value) for sample in samples] == [("cpu_pct", 91.0)]
    assert [(fault.code, fault.severity.value) for fault in faults] == [("BACKUP_BUSY", "warn")]
    assert command.state == CommandState.succeeded
    assert command.result_code == "OK"


async def test_duplicate_command_ack_is_terminal_and_does_not_retry(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    command = PendingCommand(
        device_id=device.id,
        command_id="backup:duplicate-ack",
        kind=CommandKind.take_backup_now,
        state=CommandState.delivering,
        attempt_count=1,
        correlation_id="corr-duplicate",
    )
    db_session.add(command)
    await db_session.commit()

    from acadiahq.agent_pb2 import CommandAck

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        for _ in range(2):
            yield AgentFrame(
                command_ack=CommandAck(
                    command_id=command.command_id,
                    success=True,
                    correlation_id=command.correlation_id,
                    code="OK",
                )
            )

    async for _ in gateway_stub.Connect(frames()):
        pass

    await db_session.refresh(command)
    assert command.state == CommandState.succeeded
    assert command.attempt_count == 1
    assert command.retryable is False


async def test_command_ack_json_payload_is_stored(gateway_stub, db_session):
    """The device's result payload must land in the durable command record
    (task 009, H1: a payload smuggled through `error` was discarded on
    success, so e.g. a configuration.read answer never reached HQ)."""
    import json

    from acadiahq.agent_pb2 import CommandAck

    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    command = PendingCommand(
        device_id=device.id,
        command_id="configuration:read:11111111-2222-3333-4444-555555555555",
        kind=CommandKind.configuration_read,
        state=CommandState.delivering,
        attempt_count=1,
        correlation_id="corr-payload",
    )
    db_session.add(command)
    await db_session.commit()

    payload = {"schema_version": 1, "config": {"system": {"hostname": "edge-1"}}}

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            command_ack=CommandAck(
                command_id=command.command_id,
                success=True,
                correlation_id=command.correlation_id,
                code="OK",
                json_payload=json.dumps(payload),
                operation="configuration.read",
                daemon="configuration",
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    await db_session.refresh(command)
    assert command.state == CommandState.succeeded
    assert command.result_error is None
    assert command.result_payload == payload


async def test_command_ack_failure_records_error_and_payload(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    command = PendingCommand(
        device_id=device.id,
        command_id="backup:failed-ack",
        kind=CommandKind.take_backup_now,
        state=CommandState.delivering,
        attempt_count=1,
        correlation_id="corr-failed",
    )
    db_session.add(command)
    await db_session.commit()

    from acadiahq.agent_pb2 import CommandAck

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            command_ack=CommandAck(
                command_id=command.command_id,
                success=False,
                correlation_id=command.correlation_id,
                code="INTERNAL",
                error="spoke not connected",
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    await db_session.refresh(command)
    assert command.state == CommandState.failed
    assert command.result_code == "INTERNAL"
    assert command.result_error == "spoke not connected"


async def _upload_round_trip(gateway_stub, device, credential, *, put: bool, report_size=None):
    """LogUploadRequest → SignedUploadUrl (client_ref echoed) → optional real
    PUT to storage → UploadComplete (T-P22)."""
    import asyncio
    import hashlib
    import urllib.request

    from acadiahq.agent_pb2 import LogUploadRequest, UploadComplete

    body = b"bundle-bytes" * 100
    got_url: asyncio.Queue = asyncio.Queue()
    seen = {}

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            log_upload_request=LogUploadRequest(
                kind=LogUploadRequest.LOG_BUNDLE, size_bytes_estimate=len(body), client_ref="c-1"
            )
        )
        url = await asyncio.wait_for(got_url.get(), 10)
        seen["url"] = url
        if put:
            req = urllib.request.Request(url.upload_url, data=body, method="PUT")
            await asyncio.to_thread(urllib.request.urlopen, req)
        yield AgentFrame(
            upload_complete=UploadComplete(
                request_ref=url.request_ref,
                success=True,
                size_bytes=report_size if report_size is not None else len(body),
                sha256=hashlib.sha256(body).hexdigest(),
            )
        )

    async for frame in gateway_stub.Connect(frames()):
        if frame.HasField("signed_upload_url"):
            await got_url.put(frame.signed_upload_url)
    return seen["url"]


async def test_upload_complete_finalises_the_row(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    url = await _upload_round_trip(gateway_stub, device, credential, put=True)
    assert url.client_ref == "c-1"
    bundle = (
        await db_session.execute(select(LogBundle).where(LogBundle.device_id == device.id))
    ).scalar_one()
    await db_session.refresh(bundle)
    assert bundle.upload_state == "complete"
    assert bundle.size_bytes == len(b"bundle-bytes" * 100)
    assert bundle.sha256 and bundle.completed_at is not None


async def test_upload_complete_without_object_fails_the_row(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    await _upload_round_trip(gateway_stub, device, credential, put=False)
    bundle = (
        await db_session.execute(select(LogBundle).where(LogBundle.device_id == device.id))
    ).scalar_one()
    await db_session.refresh(bundle)
    assert bundle.upload_state == "failed"
    assert "not found" in bundle.upload_error


async def test_heartbeat_status_snapshot_is_stored(gateway_stub, db_session):
    """T-P24: a heartbeat's DeviceStatus lands on the device record."""
    from acadiahq.agent_pb2 import DeviceStatus, ServiceState

    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    hb = _hb(str(device.id), credential)
    hb.status.CopyFrom(
        DeviceStatus(
            image_version="2026.09.23",
            running_slot="B",
            slot_confirmed=False,
            health_known=True,
            health_score=72.5,
            time_synchronized=True,
            serial="ACD-0001",
            hardware_revision="rev-c",
            services=[ServiceState(unit="sshd.service", active="active")],
            component_versions={"webconfigd": "0.1.0"},
        )
    )

    async def frames():
        yield AgentFrame(heartbeat=hb)

    async for _ in gateway_stub.Connect(frames()):
        pass
    await db_session.refresh(device)
    assert device.image_version == "2026.09.23"
    assert device.running_slot == "B"
    assert device.health_score == 72.5
    assert device.serial == "ACD-0001" and device.board_rev == "rev-c"
    assert device.status["services"] == [{"unit": "sshd.service", "active": "active"}]
    assert device.status["component_versions"] == {"webconfigd": "0.1.0"}
    assert device.status_updated_at is not None
