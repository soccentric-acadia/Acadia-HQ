"""add the T-P20 command kinds (power, OTA activation, services, log bundles,
device accounts, generic spoke operations)

Revision ID: 20260923tp20
Revises: 20260923ssh
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260923tp20"
down_revision: str | Sequence[str] | None = "20260923ssh"
branch_labels = None
depends_on = None

KINDS = (
    "reboot",
    "shutdown",
    "reboot_to_apply",
    "confirm_update",
    "rollback_update",
    "service_control",
    "log_bundle_request",
    "users_command",
    "operation_run",
)


def upgrade() -> None:
    # PostgreSQL enum values are additive. SQLite (API tests) needs no DDL.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for kind in KINDS:
            op.execute(f"ALTER TYPE command_kind ADD VALUE IF NOT EXISTS '{kind}'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values; retire rows using them first.
    pass
