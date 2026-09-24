"""Queue one durable device command (shared by the command producers)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import CommandKind
from app.models.pending_command import PendingCommand


def queue_command(
    db: AsyncSession,
    device_id: UUID,
    kind: CommandKind,
    label: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Add a PendingCommand (caller commits); returns its command_id."""
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
    return command_id
