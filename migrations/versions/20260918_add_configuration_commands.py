"""add durable configuration command kinds

Revision ID: 20260918cfg
Revises: a1b2c3d4e5f6
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260918cfg"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL enum values are additive and cannot be removed safely while
    # rows may contain them. SQLite (used by API tests) needs no DDL here.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE command_kind ADD VALUE IF NOT EXISTS 'configuration_read'")
        op.execute("ALTER TYPE command_kind ADD VALUE IF NOT EXISTS 'configuration_write'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values. The migration is
    # intentionally irreversible; rows using these kinds must be retired first.
    pass
