from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.config import get_settings
from app.db.deps import get_db
from app.models.enums import CommandKind, UserRole
from app.models.pending_command import PendingCommand
from app.schemas.configuration import ConfigurationWrite
from app.services import audit
from app.services.configuration import (
    CONFIGURATION_SCHEMA_VERSION,
    canonical_document,
    sign_document,
)
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/configuration", tags=["configuration"])

# The device contract is now implemented (Acadia-Configuration webconfigd
# validates this exact envelope; task 009, H5). The HMAC-SHA256 signature is a
# transitional form: webconfigd shape-checks it while Ed25519 key provisioning
# is not in place, mirroring istate's SignedConfig legacy policy.
_STATUS = "contract_v1_device_integrated"


async def _queue(
    *,
    device_id: UUID,
    operation: str,
    kind: CommandKind,
    values: dict,
    db: AsyncSession,
    ctx: TenantContext,
    request_id: str | None,
):
    await get_tenant_device_or_404(db, ctx, device_id)
    command_id = f"configuration:{operation}:{uuid4()}"
    document = canonical_document(
        device_id=device_id, command_id=command_id, operation=operation, values=values
    )
    signature = sign_document(document)
    correlation_id = request_id or command_id
    payload = {
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "origin": "hq",
        "config": values,
        "signature": signature,
        "signature_algorithm": "HMAC-SHA256",
        "integration_status": _STATUS,
    }
    db.add(
        PendingCommand(
            device_id=device_id,
            command_id=command_id,
            kind=kind,
            payload=payload,
            correlation_id=correlation_id,
            expires_at=datetime.now(UTC)
            + timedelta(seconds=get_settings().command_ttl_seconds),
        )
    )
    await audit.record(
        db,
        ctx,
        f"device.configuration.{operation}.request",
        target_device_id=device_id,
        payload={
            "command_id": command_id,
            "correlation_id": correlation_id,
            "signature": signature,
            "signature_algorithm": "HMAC-SHA256",
            "integration_status": _STATUS,
        },
    )
    await db.commit()
    return {
        "status": "queued",
        "integration_status": _STATUS,
        "command_id": command_id,
        "correlation_id": correlation_id,
        "signature": signature,
        "signature_algorithm": "HMAC-SHA256",
    }


@router.get("", status_code=status.HTTP_202_ACCEPTED)
async def read_configuration(
    device_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    """Queue a read; the device responds through the configuration contract."""
    return await _queue(
        device_id=device_id,
        operation="configuration.read",
        kind=CommandKind.configuration_read,
        values={},
        db=db,
        ctx=ctx,
        request_id=getattr(request.state, "request_id", None),
    )


@router.put("", status_code=status.HTTP_202_ACCEPTED)
async def write_configuration(
    device_id: UUID,
    body: ConfigurationWrite,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Queue a signed write; HQ never reports device application as success."""
    return await _queue(
        device_id=device_id,
        operation="configuration.write",
        kind=CommandKind.configuration_write,
        values=body.values,
        db=db,
        ctx=ctx,
        request_id=getattr(request.state, "request_id", None),
    )
