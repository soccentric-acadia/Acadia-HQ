"""T-P24: heartbeat DeviceStatus snapshot on the device record

Revision ID: 20260923tp24
Revises: 20260923tp22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923tp24"
down_revision: str | Sequence[str] | None = "20260923tp22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "device",
        sa.Column("status", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "device", sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("device", sa.Column("image_version", sa.String(), nullable=True))
    op.add_column("device", sa.Column("running_slot", sa.String(), nullable=True))
    op.add_column("device", sa.Column("health_score", sa.Float(), nullable=True))


def downgrade() -> None:
    for column in ("health_score", "running_slot", "image_version", "status_updated_at", "status"):
        op.drop_column("device", column)
