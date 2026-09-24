import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import SESSION_COOKIE_NAME
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User


async def make_tenant(session: AsyncSession, name: str | None = None) -> Tenant:
    tenant = Tenant(name=name or f"tenant-{uuid.uuid4().hex[:8]}")
    session.add(tenant)
    await session.flush()
    return tenant


async def make_user(
    session: AsyncSession, tenant: Tenant, role: UserRole, email: str | None = None
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
        role=role,
        auth_subject_id=f"sub-{uuid.uuid4().hex[:8]}",
    )
    session.add(user)
    await session.flush()
    return user


async def login_as(client: AsyncClient, user: User) -> None:
    """Open a real server-side session for `user` (T-P34) and set its cookie.
    Uses its own DB session so callers need not pass one; the user row must
    already be committed."""
    from app.db.base import get_session_factory
    from app.services import sessions

    async with get_session_factory()() as db:
        token = await sessions.create_session(db, await db.get(User, user.id))
        await db.commit()
    client.cookies.set(SESSION_COOKIE_NAME, token)
