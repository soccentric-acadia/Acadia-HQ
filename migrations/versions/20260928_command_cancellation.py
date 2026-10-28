"""add cancelled terminal state for durable commands

Revision ID: 20260928cancel
Revises: 20260923tp34
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260928cancel"
down_revision: str | Sequence[str] | None = "20260923tp34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE command_state ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    pass
