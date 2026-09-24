"""T-P21: artifact upload state, staged-rollout policy, device tags

Revision ID: 20260923tp21
Revises: 20260923tp20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923tp21"
down_revision: str | Sequence[str] | None = "20260923tp20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE rollout_status ADD VALUE IF NOT EXISTS 'halted'")
    op.add_column(
        "device",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("update_artifact", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column(
        "update_artifact", sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "update_rollout",
        sa.Column("policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("update_rollout", sa.Column("halted_reason", sa.String(), nullable=True))
    op.add_column(
        "update_rollout",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.add_column(
        "update_rollout_device",
        sa.Column("wave", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("update_rollout_device", sa.Column("command_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("update_rollout_device", "command_id")
    op.drop_column("update_rollout_device", "wave")
    op.drop_column("update_rollout", "created_at")
    op.drop_column("update_rollout", "halted_reason")
    op.drop_column("update_rollout", "policy")
    op.drop_column("update_artifact", "uploaded_at")
    op.drop_column("update_artifact", "size_bytes")
    op.drop_column("device", "tags")
    # 'halted' stays in rollout_status (PostgreSQL cannot drop enum values).
