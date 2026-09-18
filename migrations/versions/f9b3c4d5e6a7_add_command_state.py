"""add durable command state

Revision ID: f9b3c4d5e6a7
Revises: e8a2b3c4d5f6
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f9b3c4d5e6a7"
down_revision: str | Sequence[str] | None = "e8a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    state = sa.Enum(
        "queued",
        "delivering",
        "succeeded",
        "failed",
        "expired",
        name="command_state",
    )
    state.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "pending_command",
        sa.Column("state", state, nullable=False, server_default="queued"),
    )
    op.create_index("ix_pending_command_state", "pending_command", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pending_command_state", table_name="pending_command")
    op.drop_column("pending_command", "state")
    sa.Enum(name="command_state").drop(op.get_bind(), checkfirst=True)
