"""T-P22: upload state for backups and log bundles (UploadComplete)

Revision ID: 20260923tp22
Revises: 20260923tp21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923tp22"
down_revision: str | Sequence[str] | None = "20260923tp21"
branch_labels = None
depends_on = None

TABLES = ("backup", "log_bundle")


def upgrade() -> None:
    for table in TABLES:
        # Existing rows were created optimistically on the upload request and
        # were never confirmed — they are "unverified", not "complete".
        op.add_column(
            table,
            sa.Column("upload_state", sa.String(), nullable=False,
                      server_default="unverified"),
        )
        op.create_index(f"ix_{table}_upload_state", table, ["upload_state"])
        op.add_column(table, sa.Column("sha256", sa.String(), nullable=True))
        op.add_column(table, sa.Column("upload_error", sa.String(), nullable=True))
        op.add_column(
            table, sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "completed_at")
        op.drop_column(table, "upload_error")
        op.drop_column(table, "sha256")
        op.drop_index(f"ix_{table}_upload_state", table_name=table)
        op.drop_column(table, "upload_state")
