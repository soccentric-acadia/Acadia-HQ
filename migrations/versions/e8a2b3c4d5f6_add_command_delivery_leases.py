"""add durable command delivery leases

Revision ID: e8a2b3c4d5f6
Revises: d7f1e2a3b4c5
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8a2b3c4d5f6"
down_revision: str | Sequence[str] | None = "d7f1e2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pending_command",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("pending_command", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("pending_command", "lease_until")
    op.drop_column("pending_command", "attempt_count")
