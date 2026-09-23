"""gRPC glue: AgentLink.Connect bidi stream. Business logic per frame type
lives in handlers.py; this module owns connection lifecycle, auth, and
dispatch.

Auth model: only PairingHandshake and Heartbeat frames carry a credential
token (see proto/acadiahq/agent.proto) -- there's no per-frame token on
TelemetryBatch/FaultEvent/etc. So the full token comparison happens once at
connect and again on every Heartbeat (which the device sends periodically
throughout the connection); between heartbeats, every inbound frame still
re-checks the device's live `pairing_state` (cheap, no hashing) so a
disable/revoke takes effect within one heartbeat interval rather than only
at the next reconnect -- this is the practical reading of
IMPLEMENTATION_PLAN §2.2's "checked on each frame."
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC

import grpc
from sqlalchemy import select

from app.db.base import get_session_factory
from app.models.device import Device
from app.models.enums import CommandKind, CommandState, PairingState
from app.models.pending_command import PendingCommand
from app.services import audit
from app.config import get_settings
from acadiahq.agent_pb2 import (
    ApplyUpdate,
    Command,
    FactoryReset,
    HeartbeatAck,
    PairingResult,
    Restore,
    ServerFrame,
    SignedUploadUrl,
    TakeBackupNow,
)
from acadiahq.agent_pb2_grpc import AgentLinkServicer as _AgentLinkServicer

from gateway import handlers
from gateway.auth import PairingError, redeem_pairing_token, validate_long_lived_credential
from gateway.config import get_gateway_settings
from gateway.connection_manager import manager

logger = logging.getLogger("gateway.servicer")
SUPPORTED_PROTOCOL_VERSION = 1


class AgentLinkServicer(_AgentLinkServicer):
    async def Connect(self, request_iterator, context):
        session_factory = get_session_factory()

        first = await _anext_or_none(request_iterator)
        if first is None:
            return

        if first.HasField("pairing_handshake"):
            token = first.pairing_handshake.pairing_token
            async with session_factory() as session:
                async for out in self._handle_pairing(session, token):
                    yield out
            return  # device reconnects with a Heartbeat using its new credential

        if not first.HasField("heartbeat"):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "first frame must be pairing_handshake or heartbeat",
            )
            return

        device_id = first.heartbeat.device_id
        if (
            first.heartbeat.protocol_version
            and first.heartbeat.protocol_version != SUPPORTED_PROTOCOL_VERSION
        ):
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"unsupported device protocol version {first.heartbeat.protocol_version}",
            )
            return
        async with session_factory() as session:
            device = await validate_long_lived_credential(
                session, device_id, first.heartbeat.credential_token
            )
            if device is None:
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "invalid credential or device disabled"
                )
                return
            became_online = not device.online
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            if became_online:
                await audit.record_system(
                    session, device, "device.online", payload={"reason": "connect"}
                )
            await session.commit()

        settings = get_gateway_settings()
        queue = manager.register(device_id)
        dispatcher_task = asyncio.create_task(
            self._dispatch_pending_commands(device_id, queue, session_factory)
        )
        try:
            yield ServerFrame(
                heartbeat_ack=HeartbeatAck(
                    server_time_unix_ms=_now_ms(),
                    next_heartbeat_interval_s=settings.device_heartbeat_interval_s,
                    protocol_version=SUPPORTED_PROTOCOL_VERSION,
                )
            )
            async for out in self._pump(request_iterator, queue, device_id, session_factory):
                yield out
        finally:
            dispatcher_task.cancel()
            manager.unregister(device_id, queue)
            async with session_factory() as session:
                device = await session.get(Device, device_id)
                if device is not None and not manager.is_connected(device_id) and device.online:
                    device.online = False
                    await audit.record_system(
                        session, device, "device.offline", payload={"reason": "stream_closed"}
                    )
                    await session.commit()

    async def _dispatch_pending_commands(self, device_id, queue, session_factory):
        """Claim durable API commands and deliver them to this live session.

        The API and gateway are separate processes, so the database row is
        the handoff. ``delivered_at`` is the lease marker; command results
        remain durable even if the stream disappears after delivery.
        """
        operations = {
            CommandKind.take_backup_now: (
                "backup",
                lambda payload: dict(take_backup_now=TakeBackupNow()),
            ),
            CommandKind.restore: (
                "restore",
                lambda payload: dict(
                    restore=Restore(backup_download_url=payload.get("backup_download_url", ""))
                ),
            ),
            CommandKind.factory_reset: (
                "factory_reset",
                # The device gate (hq_bridge REQUIRED_FACTORY_RESET_CONFIRMATION):
                # an HQ factory reset without this confirmation is refused
                # on-device (task 009, H4).
                lambda payload: dict(
                    factory_reset=FactoryReset(),
                    required_confirmation="FACTORY-RESET",
                ),
            ),
            CommandKind.apply_update: (
                "apply_update",
                lambda payload: dict(
                    apply_update=ApplyUpdate(
                        artifact_id=payload.get("artifact_id", ""),
                        artifact_download_url=payload.get("artifact_download_url", ""),
                        checksum_sha256=payload.get("checksum_sha256", ""),
                    )
                ),
            ),
            CommandKind.configuration_read: (
                "configuration.read",
                lambda payload: dict(
                    json_args=json.dumps(payload, sort_keys=True, separators=(",", ":"))
                ),
            ),
            CommandKind.configuration_write: (
                "configuration.write",
                lambda payload: dict(
                    json_args=json.dumps(payload, sort_keys=True, separators=(",", ":"))
                ),
            ),
            # T-P11 (B05): SSH key provisioning rides the generic
            # operation/json_args fields — no proto bump needed.
            CommandKind.ssh_keys_set: (
                "ssh_keys.set",
                lambda payload: dict(
                    json_args=json.dumps(payload, sort_keys=True, separators=(",", ":"))
                ),
            ),
        }
        while True:
            async with session_factory() as session:
                now = datetime.now(UTC)
                expired = (
                    await session.execute(
                        select(PendingCommand).where(
                            PendingCommand.device_id == device_id,
                            PendingCommand.completed_at.is_(None),
                            PendingCommand.expires_at.is_not(None),
                            PendingCommand.expires_at <= now,
                        )
                    )
                ).scalars().all()
                for row in expired:
                    row.state = CommandState.expired
                    row.result_code = "DEADLINE_EXCEEDED"
                    row.result_error = "command deadline exceeded"
                    row.retryable = False
                    row.completed_at = now
                    row.lease_until = None
                rows = (
                    await session.execute(
                        select(PendingCommand)
                        .where(
                            PendingCommand.device_id == device_id,
                            PendingCommand.completed_at.is_(None),
                            (PendingCommand.expires_at.is_(None))
                            | (PendingCommand.expires_at > now),
                            (PendingCommand.lease_until.is_(None))
                            | (PendingCommand.lease_until < now),
                        )
                        .order_by(PendingCommand.created_at)
                        .limit(32)
                    )
                ).scalars().all()
                for row in rows:
                    operation = operations.get(row.kind)
                    if operation is None:
                        logger.error("unsupported pending command kind %s", row.kind)
                        row.state = CommandState.failed
                        row.result_code = "UNIMPLEMENTED"
                        row.result_error = f"unsupported command kind: {row.kind.value}"
                        row.retryable = False
                        row.completed_at = now
                        row.lease_until = None
                        continue
                    operation_name, build_kind = operation
                    row.delivered_at = datetime.now(UTC)
                    row.state = CommandState.delivering
                    row.lease_until = datetime.now(UTC) + timedelta(
                        seconds=get_settings().command_lease_seconds
                    )
                    row.attempt_count += 1
                    await queue.put(
                        ServerFrame(
                            command=Command(
                                command_id=row.command_id,
                                operation=operation_name,
                                daemon="configuration",
                                # Explicit actor + device deadline (task 009, H9):
                                # the device previously defaulted both silently.
                                actor="hq",
                                deadline_ms=get_gateway_settings().command_deadline_ms,
                                correlation_id=row.correlation_id or row.command_id,
                                idempotency_key=row.command_id,
                                **build_kind(row.payload or {}),
                            )
                        )
                    )
                await session.commit()
            await asyncio.sleep(1)

    async def _pump(self, request_iterator, queue, device_id, session_factory):
        """Interleave inbound device frames with outbound queued commands."""
        inbound_task = asyncio.ensure_future(_anext_or_none(request_iterator))
        outbound_task = asyncio.ensure_future(queue.get())
        try:
            while True:
                done, _ = await asyncio.wait(
                    {inbound_task, outbound_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if inbound_task in done:
                    frame = inbound_task.result()
                    if frame is None:
                        return
                    async with session_factory() as session:
                        still_allowed = await self._reauth(session, device_id, frame)
                        if not still_allowed:
                            return
                        response = await self._dispatch(session, device_id, frame)
                        await session.commit()
                    if response is not None:
                        yield response
                    inbound_task = asyncio.ensure_future(_anext_or_none(request_iterator))
                if outbound_task in done:
                    yield outbound_task.result()
                    outbound_task = asyncio.ensure_future(queue.get())
        finally:
            inbound_task.cancel()
            outbound_task.cancel()

    async def _reauth(self, session, device_id: str, frame) -> bool:
        if frame.HasField("heartbeat"):
            device = await validate_long_lived_credential(
                session, device_id, frame.heartbeat.credential_token
            )
            return device is not None
        # Non-heartbeat frames carry no token; cheaply confirm the device
        # hasn't been disabled/revoked mid-connection.

        device = await session.get(Device, device_id)
        return device is not None and device.pairing_state not in (
            PairingState.disabled,
            PairingState.revoked,
        )

    async def _dispatch(self, session, device_id: str, frame) -> ServerFrame | None:

        device = await session.get(Device, device_id)
        if device is None:
            return None

        if frame.HasField("heartbeat"):
            if (
                frame.heartbeat.protocol_version
                and frame.heartbeat.protocol_version != SUPPORTED_PROTOCOL_VERSION
            ):
                return False
            became_online = not device.online
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            if became_online:
                await audit.record_system(
                    session, device, "device.online", payload={"reason": "heartbeat"}
                )
            return None
        if frame.HasField("telemetry_batch"):
            became_online = not device.online
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            if became_online:
                await audit.record_system(
                    session, device, "device.online", payload={"reason": "telemetry"}
                )
            await handlers.handle_telemetry_batch(session, device, frame.telemetry_batch)
            return None
        if frame.HasField("fault_event"):
            await handlers.handle_fault_event(session, device, frame.fault_event)
            return None
        if frame.HasField("log_upload_request"):
            request_ref, url, expires_in = await handlers.handle_log_upload_request(
                session, device, frame.log_upload_request
            )
            return ServerFrame(
                signed_upload_url=SignedUploadUrl(
                    request_ref=request_ref,
                    upload_url=url,
                    expires_at_unix_ms=_now_ms() + expires_in * 1000,
                )
            )
        if frame.HasField("command_ack"):
            ack = frame.command_ack
            await handlers.handle_command_ack(
                session,
                device,
                ack.command_id,
                ack.success,
                ack.error,
                correlation_id=ack.correlation_id,
                code=ack.code,
                daemon=ack.daemon,
                operation=ack.operation,
                json_payload=ack.json_payload,
                retryable=ack.retryable,
            )
            return None
        return None

    async def _handle_pairing(self, session, raw_token: str):
        try:
            device, long_lived = await redeem_pairing_token(session, raw_token)
            await session.commit()
        except PairingError as exc:
            yield ServerFrame(pairing_result=PairingResult(success=False, error=str(exc)))
            return
        yield ServerFrame(
            pairing_result=PairingResult(
                success=True, device_id=str(device.id), credential_token=long_lived
            )
        )


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


async def _anext_or_none(iterator):
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        return None
