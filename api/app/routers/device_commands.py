"""T-P20: device command producers — power, OTA activation, services, log
bundles, local device accounts and allowlisted spoke operations.

Every endpoint queues one durable ``PendingCommand``; the agent-gateway maps
it onto the AgentLink ``Command`` (gateway/command_map.py) and the device
executes it (Acadia-Configuration hq_command_handler.rs). Results are read
back through ``GET /devices/{id}/commands/{command_id}``.

Destructive verbs require the operator to type the same confirmation word
the device demands (SHUTDOWN, ROLLBACK), so a stray click cannot queue them.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.config import get_settings
from app.db.deps import get_db
from app.models.enums import CommandKind, UserRole
from app.models.pending_command import PendingCommand
from app.services import audit
from app.services.device_scope import get_tenant_device_or_404
from app.services.operation_catalog import SPOKE_OPERATIONS
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}", tags=["device-commands"])

_RANK = {UserRole.viewer: 0, UserRole.operator: 1, UserRole.admin: 2}


async def _queue(
    db: AsyncSession,
    ctx: TenantContext,
    device_id: UUID,
    kind: CommandKind,
    label: str,
    payload: dict[str, Any] | None = None,
    audit_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    await get_tenant_device_or_404(db, ctx, device_id)
    command_id = f"{label}:{uuid4()}"
    db.add(
        PendingCommand(
            device_id=device_id,
            command_id=command_id,
            kind=kind,
            payload=payload or {},
            correlation_id=command_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().command_ttl_seconds),
        )
    )
    await audit.record(
        db,
        ctx,
        f"device.{label}.request",
        target_device_id=device_id,
        payload={"command_id": command_id, **(audit_payload or {})},
    )
    await db.commit()
    return {"status": "queued", "command_id": command_id, "correlation_id": command_id}


class Confirmation(BaseModel):
    confirmation: str


def _confirm(body: Confirmation, word: str) -> None:
    if body.confirmation != word:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"type {word} to confirm")


# ── Power (C04/C05) ───────────────────────────────────────────────────────


@router.post("/power/reboot", status_code=status.HTTP_202_ACCEPTED)
async def reboot(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    return await _queue(db, ctx, device_id, CommandKind.reboot, "power.reboot")


@router.post("/power/shutdown", status_code=status.HTTP_202_ACCEPTED)
async def shutdown(
    device_id: UUID,
    body: Confirmation,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Admin only: HQ cannot power the unit back on."""
    _confirm(body, "SHUTDOWN")
    return await _queue(db, ctx, device_id, CommandKind.shutdown, "power.shutdown")


# ── OTA activation (K10) ──────────────────────────────────────────────────


@router.post("/updates/reboot-to-apply", status_code=status.HTTP_202_ACCEPTED)
async def reboot_to_apply(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    return await _queue(db, ctx, device_id, CommandKind.reboot_to_apply, "update.reboot_to_apply")


@router.post("/updates/confirm", status_code=status.HTTP_202_ACCEPTED)
async def confirm_update(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    return await _queue(db, ctx, device_id, CommandKind.confirm_update, "update.confirm")


@router.post("/updates/rollback", status_code=status.HTTP_202_ACCEPTED)
async def rollback_update(
    device_id: UUID,
    body: Confirmation,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    _confirm(body, "ROLLBACK")
    return await _queue(db, ctx, device_id, CommandKind.rollback_update, "update.rollback")


# ── Services (G02) ────────────────────────────────────────────────────────


class ServiceControl(BaseModel):
    unit: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9@._+-]+$")
    action: Literal["start", "stop", "restart", "enable", "disable"]


@router.post("/services/control", status_code=status.HTTP_202_ACCEPTED)
async def service_control(
    device_id: UUID,
    body: ServiceControl,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """The device enforces its board-manifest service allowlist."""
    payload = body.model_dump()
    return await _queue(
        db, ctx, device_id, CommandKind.service_control, "service.control", payload, payload
    )


# ── Log bundles (J04) ─────────────────────────────────────────────────────


@router.post("/logs/request", status_code=status.HTTP_202_ACCEPTED)
async def request_log_bundle(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """The device creates a support bundle and uploads it; it then appears in
    ``GET /devices/{id}/logs``."""
    return await _queue(db, ctx, device_id, CommandKind.log_bundle_request, "log_bundle.request")


# ── Local device accounts (B02) ───────────────────────────────────────────


class DeviceUserCommand(BaseModel):
    operation: Literal["users.list", "users.create", "users.delete", "users.set_role"]
    username: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    role: Literal["admin", "operator", "viewer"] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)


@router.post("/users/command", status_code=status.HTTP_202_ACCEPTED)
async def device_users(
    device_id: UUID,
    body: DeviceUserCommand,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Manage the device's local web-UI accounts. The initial password of
    ``users.create`` is scrubbed from HQ's database once delivered."""
    if body.operation != "users.list" and not body.username:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "username is required")
    if body.operation in ("users.create", "users.set_role") and not body.role:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role is required")
    if body.operation == "users.create" and not body.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "password is required")
    payload = body.model_dump(exclude_none=True)
    audit_payload = {k: v for k, v in payload.items() if k != "password"}
    return await _queue(
        db, ctx, device_id, CommandKind.users_command, body.operation, payload, audit_payload
    )


# ── Generic allowlisted spoke operation (N05) ─────────────────────────────


class SpokeOperation(BaseModel):
    daemon: str = Field(min_length=1, max_length=32)
    operation: str = Field(min_length=1, max_length=64)
    args: dict[str, Any] = Field(default_factory=dict)


@router.post("/operations", status_code=status.HTTP_202_ACCEPTED)
async def run_operation(
    device_id: UUID,
    body: SpokeOperation,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Run one Instrumentation spoke operation from ``SPOKE_OPERATIONS``."""
    minimum = SPOKE_OPERATIONS.get((body.daemon, body.operation))
    if minimum is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, f"{body.daemon}.{body.operation} is not allowlisted"
        )
    if _RANK[UserRole(ctx.role)] < _RANK[UserRole(minimum)]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires {minimum} role")
    payload = body.model_dump()
    return await _queue(
        db,
        ctx,
        device_id,
        CommandKind.operation_run,
        f"operation.{body.daemon}.{body.operation}",
        payload,
        {"daemon": body.daemon, "operation": body.operation},
    )
