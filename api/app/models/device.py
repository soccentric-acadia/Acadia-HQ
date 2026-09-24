from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PairingState
from app.models.mixins import TenantScopedMixin

if TYPE_CHECKING:
    from app.models.device_credential import DeviceCredential


class Device(Base, TenantScopedMixin):
    __tablename__ = "device"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_device_tenant_name"),)

    name: Mapped[str] = mapped_column(index=True)
    pairing_state: Mapped[PairingState] = mapped_column(
        Enum(PairingState, name="pairing_state"), default=PairingState.pending, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Hardware identity, populated once the device actually pairs (Phase 2)
    # from Acadia-Configuration's board manifest -- absent for pre-provisioned
    # (pending) devices.
    serial: Mapped[str | None] = mapped_column(nullable=True)
    board_rev: Mapped[str | None] = mapped_column(nullable=True)
    # T-P21 (N06): operator-assigned tags for grouping and rollout targeting.
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # T-P24 (C03/H03/K07/D07/G01): the last heartbeat DeviceStatus snapshot.
    # `status` keeps the full snapshot; the scalar columns are the fields
    # the fleet list and the health score read directly.
    status: Mapped[dict] = mapped_column(JSONB, default=dict)
    status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    image_version: Mapped[str | None] = mapped_column(nullable=True)
    running_slot: Mapped[str | None] = mapped_column(nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    credentials: Mapped[list["DeviceCredential"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
