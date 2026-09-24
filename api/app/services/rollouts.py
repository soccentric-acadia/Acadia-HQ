"""T-P21 (K09/K11/N06): staged OTA rollout engine.

One rollout = one verified artifact → a set of target devices, split into
two waves:

* **wave 0 (canary)** — ``canary_percent`` of the targets (at least one);
* **wave 1** — everyone else, queued only when the canary finished with a
  failure rate at or below ``halt_failure_percent``.

Each device gets a durable ``apply_update`` command (``update:<rollout>:
<device>``); the device downloads the artifact through a presigned URL,
verifies the SHA-256 and the bundle, and installs to the inactive slot.
With ``auto_activate`` a successful install is followed by a
``reboot_to_apply`` command; the device's health-gated boot check confirms
the slot (or the firmware rolls back).

The same functions run in the API (create/start/halt/resume) and in the
agent-gateway's command-ack handler (per-device results), so the rollout
advances without a separate worker process.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.device import Device
from app.models.enums import (
    CommandKind,
    DeviceRolloutStatus,
    RolloutStatus,
    RolloutTarget,
)
from app.models.pending_command import PendingCommand
from app.models.update import UpdateArtifact, UpdateRollout, UpdateRolloutDevice
from app.services.storage import presigned_download_url

DEFAULT_POLICY: dict[str, Any] = {
    "canary_percent": 10,
    "halt_failure_percent": 20,
    "auto_activate": True,
}

# The artifact URL must outlive the command: queued commands wait for an
# offline device up to the command TTL, then download a multi-GB bundle.
DOWNLOAD_URL_GRACE = timedelta(hours=6)

TERMINAL = (DeviceRolloutStatus.succeeded, DeviceRolloutStatus.failed)


class RolloutError(ValueError):
    """A rollout request that cannot be honoured (maps to HTTP 400/409)."""


def normalise_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    merged = {**DEFAULT_POLICY, **(policy or {})}
    canary = int(merged["canary_percent"])
    halt = int(merged["halt_failure_percent"])
    if not 1 <= canary <= 100:
        raise RolloutError("canary_percent must be 1..100")
    if not 0 <= halt <= 100:
        raise RolloutError("halt_failure_percent must be 0..100")
    return {
        "canary_percent": canary,
        "halt_failure_percent": halt,
        "auto_activate": bool(merged["auto_activate"]),
    }


async def select_targets(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target: RolloutTarget,
    selector: dict[str, Any],
) -> list[Device]:
    query = select(Device).where(Device.tenant_id == tenant_id)
    devices = (await db.execute(query.order_by(Device.id))).scalars().all()
    if target == RolloutTarget.all:
        return list(devices)
    if target == RolloutTarget.specific_devices:
        wanted = {str(d) for d in selector.get("device_ids", [])}
        chosen = [d for d in devices if str(d.id) in wanted]
        if len(chosen) != len(wanted):
            raise RolloutError("device_ids contains devices outside this tenant")
        return chosen
    if target == RolloutTarget.device_group:
        tag = selector.get("tag")
        if not tag:
            raise RolloutError("device_group rollouts need a tag")
        return [d for d in devices if tag in (d.tags or [])]
    raise RolloutError(f"unsupported target {target}")


async def create_rollout(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    artifact: UpdateArtifact,
    target: RolloutTarget,
    selector: dict[str, Any],
    policy: dict[str, Any] | None,
) -> UpdateRollout:
    if artifact.uploaded_at is None:
        raise RolloutError("artifact content has not been uploaded and verified yet")
    policy = normalise_policy(policy)
    devices = await select_targets(db, tenant_id, target, selector)
    if not devices:
        raise RolloutError("the rollout target matches no devices")
    rollout = UpdateRollout(
        artifact_id=artifact.id,
        target=target,
        target_selector=selector,
        status=RolloutStatus.pending,
        policy=policy,
    )
    db.add(rollout)
    await db.flush()
    canary = max(1, math.ceil(len(devices) * policy["canary_percent"] / 100))
    for index, device in enumerate(devices):
        db.add(
            UpdateRolloutDevice(
                rollout_id=rollout.id,
                device_id=device.id,
                status=DeviceRolloutStatus.pending,
                wave=0 if index < canary else 1,
            )
        )
    await db.flush()
    return rollout


async def _rows(db: AsyncSession, rollout_id: uuid.UUID) -> list[UpdateRolloutDevice]:
    return list(
        (
            await db.execute(
                select(UpdateRolloutDevice).where(UpdateRolloutDevice.rollout_id == rollout_id)
            )
        ).scalars()
    )


def _command(
    device_id: uuid.UUID, command_id: str, kind: CommandKind, payload: dict
) -> PendingCommand:
    return PendingCommand(
        device_id=device_id,
        command_id=command_id,
        kind=kind,
        payload=payload,
        correlation_id=command_id,
        expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().command_ttl_seconds),
    )


async def queue_wave(db: AsyncSession, rollout: UpdateRollout, wave: int) -> int:
    """Queue ``apply_update`` for every pending device of ``wave``."""
    artifact = await db.get(UpdateArtifact, rollout.artifact_id)
    if artifact is None:
        raise RolloutError("artifact no longer exists")
    url_ttl = get_settings().command_ttl_seconds + int(DOWNLOAD_URL_GRACE.total_seconds())
    queued = 0
    for row in await _rows(db, rollout.id):
        if row.wave != wave or row.status != DeviceRolloutStatus.pending:
            continue
        command_id = f"update:{rollout.id}:{row.device_id}"
        db.add(
            _command(
                row.device_id,
                command_id,
                CommandKind.apply_update,
                {
                    "artifact_id": artifact.version,
                    "artifact_download_url": presigned_download_url(
                        artifact.storage_url, expires_in=url_ttl
                    ),
                    "checksum_sha256": artifact.checksum_sha256,
                },
            )
        )
        row.status = DeviceRolloutStatus.applying
        row.command_id = command_id
        queued += 1
    return queued


async def start(db: AsyncSession, rollout: UpdateRollout) -> int:
    if rollout.status != RolloutStatus.pending:
        raise RolloutError(f"rollout is {rollout.status.value}, not pending")
    rollout.status = RolloutStatus.in_progress
    rollout.started_at = datetime.now(UTC)
    return await queue_wave(db, rollout, 0)


async def halt(db: AsyncSession, rollout: UpdateRollout, reason: str) -> None:
    if rollout.status not in (RolloutStatus.pending, RolloutStatus.in_progress):
        raise RolloutError(f"rollout is {rollout.status.value}")
    rollout.status = RolloutStatus.halted
    rollout.halted_reason = reason


async def resume(db: AsyncSession, rollout: UpdateRollout) -> int:
    """Continue a halted rollout: the canary wave if it never finished,
    otherwise the remainder (an operator override of the failure gate)."""
    if rollout.status != RolloutStatus.halted:
        raise RolloutError(f"rollout is {rollout.status.value}, not halted")
    rollout.status = RolloutStatus.in_progress
    rollout.halted_reason = None
    rows = await _rows(db, rollout.id)
    canary_done = all(r.status in TERMINAL for r in rows if r.wave == 0)
    return await queue_wave(db, rollout, 1 if canary_done else 0)


def summarise(rows: list[UpdateRolloutDevice]) -> dict[str, Any]:
    counts = {s.value: 0 for s in DeviceRolloutStatus}
    for r in rows:
        counts[r.status.value] += 1
    return {"total": len(rows), **counts}


async def record_device_result(
    db: AsyncSession,
    rollout_id: uuid.UUID,
    device_id: uuid.UUID,
    success: bool,
    error: str | None,
) -> None:
    """Apply one device's ``apply_update`` outcome and advance the rollout."""
    row = await db.get(UpdateRolloutDevice, {"rollout_id": rollout_id, "device_id": device_id})
    rollout = await db.get(UpdateRollout, rollout_id)
    if row is None or rollout is None:
        return
    row.status = DeviceRolloutStatus.succeeded if success else DeviceRolloutStatus.failed
    row.applied_at = datetime.now(UTC)
    row.error = None if success else (error or "failed")
    policy = normalise_policy(rollout.policy)
    if success and policy["auto_activate"]:
        db.add(
            _command(
                device_id,
                f"update-activate:{rollout_id}:{device_id}",
                CommandKind.reboot_to_apply,
                {},
            )
        )
    await db.flush()
    await advance(db, rollout)


async def advance(db: AsyncSession, rollout: UpdateRollout) -> None:
    """Gate the canary and close the rollout once every device is terminal."""
    if rollout.status != RolloutStatus.in_progress:
        return
    rows = await _rows(db, rollout.id)
    policy = normalise_policy(rollout.policy)
    canary = [r for r in rows if r.wave == 0]
    rest = [r for r in rows if r.wave == 1]
    if canary and all(r.status in TERMINAL for r in canary):
        failed = sum(r.status == DeviceRolloutStatus.failed for r in canary)
        failure_pct = 100 * failed / len(canary)
        pending_rest = [r for r in rest if r.status == DeviceRolloutStatus.pending]
        if pending_rest:
            if failure_pct > policy["halt_failure_percent"]:
                rollout.status = RolloutStatus.halted
                rollout.halted_reason = (
                    f"canary failure rate {failure_pct:.0f}% exceeds "
                    f"{policy['halt_failure_percent']}%"
                )
                return
            await queue_wave(db, rollout, 1)
            return
    if rows and all(r.status in TERMINAL for r in rows):
        failed = sum(r.status == DeviceRolloutStatus.failed for r in rows)
        rollout.completed_at = datetime.now(UTC)
        rollout.status = (
            RolloutStatus.failed
            if 100 * failed / len(rows) > policy["halt_failure_percent"]
            else RolloutStatus.completed
        )
