"""T-P34: server-side sessions; user deactivation

Revision ID: 20260923tp34
Revises: 20260923tp24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923tp34"
down_revision: str | Sequence[str] | None = "20260923tp24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "user_session",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_table("user_session")
    op.drop_column("user", "is_active")
