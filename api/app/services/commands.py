"""Queue one durable device command (shared by the command producers)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import CommandKind, CommandState
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


async def cancel_queued_command(
    db: AsyncSession, device_id: UUID, command_id: str, now: datetime
) -> bool:
    """Atomically cancel a queued command.

    A zero-row result means dispatch claimed the command or another writer
    terminally completed it; callers must read its resulting state before
    choosing their response.
    """
    result = await db.execute(
        update(PendingCommand)
        .where(
            PendingCommand.device_id == device_id,
            PendingCommand.command_id == command_id,
            PendingCommand.state == CommandState.queued,
            PendingCommand.completed_at.is_(None),
        )
        .values(
            state=CommandState.cancelled,
            result_code="CANCELLED",
            result_error="cancelled by operator",
            retryable=False,
            completed_at=now,
            lease_until=None,
        )
        .returning(PendingCommand.id)
    )
    return result.scalar_one_or_none() is not None
