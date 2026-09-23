"""Device update + factory-reset command producers (task 009, H10).

The gateway and the device agent both supported `apply_update` and
`factory_reset` commands, but no API endpoint ever queued them — the enum and
the dispatcher were dead code. These endpoints close the producer side.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.config import get_settings
from app.db.deps import get_db
from app.models.enums import CommandKind, UserRole
from app.models.pending_command import PendingCommand
from app.services import audit
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/updates", tags=["updates"])


class ApplyUpdateRequest(BaseModel):
    """A signed update artifact the device should download and install."""

    artifact_id: str = Field(min_length=1)
    artifact_download_url: str = Field(min_length=1)
    checksum_sha256: str = Field(min_length=64, max_length=64)


@router.post("/apply", status_code=202)
async def apply_update(
    device_id: UUID,
    body: ApplyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Queue an ApplyUpdate command for the device.

    The device downloads the artifact, verifies the declared SHA-256, verifies
    and installs the bundle; reboot-to-apply remains operator-controlled
    (commit/confirm rollback window, Acadia-Configuration spec §4.2).
    """
    await get_tenant_device_or_404(db, ctx, device_id)
    command_id = f"apply-update:{body.artifact_id}"
    expires_at = datetime.now(UTC) + timedelta(seconds=get_settings().command_ttl_seconds)
    db.add(
        PendingCommand(
            device_id=device_id,
            command_id=command_id,
            kind=CommandKind.apply_update,
            payload={
                "artifact_id": body.artifact_id,
                "artifact_download_url": body.artifact_download_url,
                "checksum_sha256": body.checksum_sha256,
            },
            correlation_id=command_id,
            expires_at=expires_at,
        )
    )
    await audit.record(
        db,
        ctx,
        "device.update.apply.request",
        target_device_id=device_id,
        payload={"artifact_id": body.artifact_id},
    )
    await db.commit()
    return {"ok": True, "command_id": command_id}


@router.post("/factory-reset", status_code=202)
async def factory_reset(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Queue a FactoryReset command (admin only).

    The device requires the `FACTORY-RESET` confirmation the gateway attaches;
    wiping user accounts stays a local, operator-confirmed action.
    """
    await get_tenant_device_or_404(db, ctx, device_id)
    command_id = f"factory-reset:{uuid4()}"
    expires_at = datetime.now(UTC) + timedelta(seconds=get_settings().command_ttl_seconds)
    db.add(
        PendingCommand(
            device_id=device_id,
            command_id=command_id,
            kind=CommandKind.factory_reset,
            correlation_id=command_id,
            expires_at=expires_at,
        )
    )
    await audit.record(db, ctx, "device.factory_reset.request", target_device_id=device_id)
    await db.commit()
    return {"ok": True, "command_id": command_id}