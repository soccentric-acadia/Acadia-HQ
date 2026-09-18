"""Add command expiry timestamps.

Revision ID: a1b2c3d4e5f6
Revises: f9b3c4d5e6a7
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f9b3c4d5e6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pending_command",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_pending_command_expires_at",
        "pending_command",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pending_command_expires_at", table_name="pending_command")
    op.drop_column("pending_command", "expires_at")
