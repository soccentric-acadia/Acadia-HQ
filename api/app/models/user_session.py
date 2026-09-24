"""Server-side sessions (T-P34, HQ-005/006).

The session JWT carries only a session id (`sid`); this row decides whether
the session is still valid. Logout and user deactivation revoke rows, so a
stolen or old cookie stops working immediately instead of living out its
8 h TTL, and the caller's role is read from the user row on every request
(a demotion applies at once).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserSession(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_session"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
