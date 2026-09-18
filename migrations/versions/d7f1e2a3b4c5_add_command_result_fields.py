"""add structured command result fields

Revision ID: d7f1e2a3b4c5
Revises: c1a2b3c4d5e6
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7f1e2a3b4c5"
down_revision: str | Sequence[str] | None = "c1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pending_command", sa.Column("correlation_id", sa.String(), nullable=True))
    op.add_column("pending_command", sa.Column("result_code", sa.String(), nullable=True))
    op.add_column("pending_command", sa.Column("result_error", sa.Text(), nullable=True))
    op.add_column(
        "pending_command",
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("pending_command", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pending_command", sa.Column("retryable", sa.Boolean(), nullable=True))
    op.create_index(
        "ix_pending_command_correlation_id", "pending_command", ["correlation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_pending_command_correlation_id", table_name="pending_command")
    for name in ("retryable", "completed_at", "result_payload", "result_error", "result_code", "correlation_id"):
        op.drop_column("pending_command", name)
