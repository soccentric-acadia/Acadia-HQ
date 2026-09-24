"""Session lifecycle (T-P34, HQ-005/006)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import InvalidSession, issue_session_token, verify_session_token
from app.config import get_settings
from app.models.user import User
from app.models.user_session import UserSession
from app.services.tenant_repo import TenantContext


async def create_session(db: AsyncSession, user: User) -> str:
    """Persist a session for `user` and return its cookie token."""
    sid = uuid.uuid4()
    db.add(
        UserSession(
            id=sid,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().session_ttl_seconds),
        )
    )
    await db.flush()
    return issue_session_token(user.id, user.tenant_id, user.role.value, sid)


async def resolve(db: AsyncSession, token: str) -> TenantContext | None:
    """The caller's context for a cookie token, or None when the session is
    unknown, revoked, expired, or its user is gone/deactivated. The role comes
    from the user row, never from the token."""
    try:
        claims = verify_session_token(token)
        sid = uuid.UUID(claims["sid"])
    except (InvalidSession, KeyError, ValueError):
        return None
    session = await db.get(UserSession, sid)
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(UTC):
        return None
    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    return TenantContext(tenant_id=user.tenant_id, user_id=user.id, role=user.role.value, sid=sid)


async def revoke(db: AsyncSession, sid: uuid.UUID) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.id == sid, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def revoke_all(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
