"""T-P21 (K09/K11/N06): OTA artifact store, staged rollouts, device tags.

* ``POST /updates/artifacts`` registers an artifact (version, board rev,
  declared SHA-256); ``PUT /updates/artifacts/{id}/content`` streams the
  ``.swu`` through HQ, which **verifies the SHA-256 before storing it** — a
  mismatching upload never becomes installable.
* ``POST /updates/rollouts`` targets all devices, explicit device ids, or a
  device tag; ``/start``, ``/halt``, ``/resume`` drive it. Advancement
  (canary gate, auto-activation, completion) runs on each device result —
  see ``app/services/rollouts.py``.
* ``PUT /devices/{id}/tags`` assigns the tags that ``device_group`` rollouts
  target.
"""

import hashlib
import os
import re
import tempfile
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import RolloutTarget, UserRole
from app.models.update import UpdateArtifact, UpdateRollout, UpdateRolloutDevice
from app.services import audit, rollouts, storage
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext

router = APIRouter(tags=["fleet-updates"])

MAX_ARTIFACT_BYTES = 8 * 1024**3  # one A/B slot


class ArtifactIn(BaseModel):
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._+-]+$")
    target_board_rev: str = Field(min_length=1, max_length=64)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


def _artifact_out(a: UpdateArtifact) -> dict[str, Any]:
    return {
        "id": a.id,
        "version": a.version,
        "target_board_rev": a.target_board_rev,
        "checksum_sha256": a.checksum_sha256,
        "size_bytes": a.size_bytes,
        "uploaded_at": a.uploaded_at,
        "created_at": a.created_at,
    }


async def _artifact_or_404(db: AsyncSession, ctx: TenantContext, artifact_id: UUID):
    artifact = await db.get(UpdateArtifact, artifact_id)
    if artifact is None or artifact.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "artifact not found")
    return artifact


@router.get("/updates/artifacts")
async def list_artifacts(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    rows = (
        await db.execute(
            select(UpdateArtifact)
            .where(UpdateArtifact.tenant_id == ctx.tenant_id)
            .order_by(UpdateArtifact.created_at.desc())
        )
    ).scalars()
    return {"items": [_artifact_out(a) for a in rows]}


@router.post("/updates/artifacts", status_code=status.HTTP_201_CREATED)
async def create_artifact(
    body: ArtifactIn,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    exists = (
        await db.execute(
            select(UpdateArtifact).where(
                UpdateArtifact.tenant_id == ctx.tenant_id, UpdateArtifact.version == body.version
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "an artifact with this version exists")
    artifact = UpdateArtifact(
        tenant_id=ctx.tenant_id,
        version=body.version,
        target_board_rev=body.target_board_rev,
        checksum_sha256=body.checksum_sha256.lower(),
        storage_url=f"artifacts/{ctx.tenant_id}/{body.version}.swu",
    )
    db.add(artifact)
    await db.flush()
    await audit.record(db, ctx, "update.artifact.create", payload={"version": body.version})
    await db.commit()
    return _artifact_out(artifact)


@router.put("/updates/artifacts/{artifact_id}/content")
async def upload_artifact_content(
    artifact_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Raw ``.swu`` body. Streamed to a temp file while hashing; stored only
    when the SHA-256 matches the declared one."""
    artifact = await _artifact_or_404(db, ctx, artifact_id)
    if artifact.uploaded_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "artifact content already uploaded")
    digest = hashlib.sha256()
    size = 0
    fd, path = tempfile.mkstemp(prefix="acadiahq-artifact-", suffix=".swu")
    try:
        with os.fdopen(fd, "wb") as out:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "artifact exceeds 8 GiB"
                    )
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty artifact body")
        if digest.hexdigest() != artifact.checksum_sha256:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "uploaded content does not match the declared SHA-256",
            )
        storage.upload_file(path, artifact.storage_url)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    artifact.size_bytes = size
    artifact.uploaded_at = datetime.now(UTC)
    await audit.record(
        db, ctx, "update.artifact.upload", payload={"version": artifact.version, "size": size}
    )
    await db.commit()
    return _artifact_out(artifact)


class RolloutIn(BaseModel):
    artifact_id: UUID
    target: Literal["all", "specific_devices", "device_group"]
    device_ids: list[UUID] = []
    tag: str | None = None
    canary_percent: int = Field(default=10, ge=1, le=100)
    halt_failure_percent: int = Field(default=20, ge=0, le=100)
    auto_activate: bool = True


async def _rollout_or_404(db: AsyncSession, ctx: TenantContext, rollout_id: UUID):
    rollout = await db.get(UpdateRollout, rollout_id)
    if rollout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rollout not found")
    await _artifact_or_404(db, ctx, rollout.artifact_id)
    return rollout


async def _rollout_out(db: AsyncSession, rollout: UpdateRollout) -> dict[str, Any]:
    rows = list(
        (
            await db.execute(
                select(UpdateRolloutDevice).where(UpdateRolloutDevice.rollout_id == rollout.id)
            )
        ).scalars()
    )
    artifact = await db.get(UpdateArtifact, rollout.artifact_id)
    return {
        "id": rollout.id,
        "artifact_id": rollout.artifact_id,
        "artifact_version": artifact.version if artifact else None,
        "target": rollout.target.value,
        "target_selector": rollout.target_selector,
        "status": rollout.status.value,
        "policy": rollout.policy,
        "halted_reason": rollout.halted_reason,
        "created_at": rollout.created_at,
        "started_at": rollout.started_at,
        "completed_at": rollout.completed_at,
        "summary": rollouts.summarise(rows),
        "devices": [
            {
                "device_id": r.device_id,
                "wave": r.wave,
                "status": r.status.value,
                "error": r.error,
                "applied_at": r.applied_at,
                "command_id": r.command_id,
            }
            for r in rows
        ],
    }


@router.get("/updates/rollouts")
async def list_rollouts(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    rows = (
        await db.execute(
            select(UpdateRollout)
            .join(UpdateArtifact, UpdateArtifact.id == UpdateRollout.artifact_id)
            .where(UpdateArtifact.tenant_id == ctx.tenant_id)
            .order_by(UpdateRollout.created_at.desc())
        )
    ).scalars()
    return {"items": [await _rollout_out(db, r) for r in rows]}


@router.get("/updates/rollouts/{rollout_id}")
async def get_rollout(
    rollout_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    return await _rollout_out(db, await _rollout_or_404(db, ctx, rollout_id))


@router.post("/updates/rollouts", status_code=status.HTTP_201_CREATED)
async def create_rollout(
    body: RolloutIn,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    artifact = await _artifact_or_404(db, ctx, body.artifact_id)
    selector: dict[str, Any] = {}
    if body.target == "specific_devices":
        selector = {"device_ids": [str(d) for d in body.device_ids]}
    elif body.target == "device_group":
        selector = {"tag": body.tag}
    try:
        rollout = await rollouts.create_rollout(
            db,
            ctx.tenant_id,
            artifact,
            RolloutTarget(body.target),
            selector,
            {
                "canary_percent": body.canary_percent,
                "halt_failure_percent": body.halt_failure_percent,
                "auto_activate": body.auto_activate,
            },
        )
    except rollouts.RolloutError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    await audit.record(
        db,
        ctx,
        "update.rollout.create",
        payload={"rollout_id": str(rollout.id), "version": artifact.version},
    )
    await db.commit()
    return await _rollout_out(db, rollout)


@router.post("/updates/rollouts/{rollout_id}/{action}")
async def drive_rollout(
    rollout_id: UUID,
    action: Literal["start", "halt", "resume"],
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    rollout = await _rollout_or_404(db, ctx, rollout_id)
    try:
        if action == "start":
            await rollouts.start(db, rollout)
        elif action == "halt":
            await rollouts.halt(db, rollout, "halted by operator")
        else:
            await rollouts.resume(db, rollout)
    except rollouts.RolloutError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    await audit.record(
        db, ctx, f"update.rollout.{action}", payload={"rollout_id": str(rollout_id)}
    )
    await db.commit()
    return await _rollout_out(db, rollout)


TAG_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


class TagsIn(BaseModel):
    tags: list[str] = Field(max_length=32)


@router.put("/devices/{device_id}/tags")
async def set_device_tags(
    device_id: UUID,
    body: TagsIn,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    bad = [t for t in body.tags if not TAG_RE.match(t)]
    if bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid tags: {bad}")
    device = await get_tenant_device_or_404(db, ctx, device_id)
    device.tags = sorted(set(body.tags))
    await audit.record(
        db, ctx, "device.tags.set", target_device_id=device_id, payload={"tags": device.tags}
    )
    await db.commit()
    return {"device_id": device_id, "tags": device.tags}
