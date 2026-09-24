from sqlalchemy import Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TenantScopedMixin


class User(Base, TenantScopedMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    email: Mapped[str] = mapped_column(index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.viewer
    )
    # OIDC provider's `sub` claim. Nullable so a pre-invited user row can
    # exist before the person has ever logged in.
    auth_subject_id: Mapped[str | None] = mapped_column(index=True, unique=True, nullable=True)
    # T-P34 (B08): a deactivated user cannot log in and every session they
    # hold is revoked; the row (and its audit trail) is kept.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
