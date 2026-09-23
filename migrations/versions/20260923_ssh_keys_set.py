"""add the ssh_keys_set command kind (T-P11, B05)

Revision ID: 20260923ssh
Revises: f9b3c4d5e6a7
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260923ssh"
down_revision: str | Sequence[str] | None = "20260918cfg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL enum values are additive and cannot be removed safely while
    # rows may contain them. SQLite (used by API tests) needs no DDL here.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE command_kind ADD VALUE IF NOT EXISTS 'ssh_keys_set'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values. The migration is
    # intentionally irreversible; rows using this kind must be retired first.
    pass
