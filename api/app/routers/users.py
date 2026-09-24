from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserInvite, UserOut
from app.services import audit, sessions
from app.services.tenant_repo import TenantContext, TenantRepo

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    users = (await db.execute(repo.scoped(User).order_by(User.email))).scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post("/invite", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: UserInvite,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    user = repo.stamp_tenant(User(email=body.email, role=body.role))
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "user already exists for this tenant"
        ) from exc

    await audit.record(
        db, ctx, "user.invite", payload={"email": body.email, "role": body.role.value}
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── T-P34 (B08): role change, deactivation, removal ──────────────────────


class RoleChange(BaseModel):
    role: UserRole


async def _target(db: AsyncSession, ctx: TenantContext, user_id: UUID) -> User:
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if user.id == ctx.user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "you cannot change your own account")
    return user


async def _guard_last_admin(db: AsyncSession, ctx: TenantContext, user: User) -> None:
    if user.role != UserRole.admin or not user.is_active:
        return
    admins = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == ctx.tenant_id,
                User.role == UserRole.admin,
                User.is_active.is_(True),
            )
        )
    ).scalar_one()
    if admins <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "the tenant must keep an active admin")


@router.patch("/{user_id}", response_model=UserOut)
async def change_role(
    user_id: UUID,
    body: RoleChange,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Takes effect on the user's next request — the role is read from the
    user row, not the session token."""
    user = await _target(db, ctx, user_id)
    if body.role != UserRole.admin:
        await _guard_last_admin(db, ctx, user)
    old = user.role
    user.role = body.role
    await audit.record(
        db,
        ctx,
        "user.role",
        payload={"user_id": str(user_id), "from": old.value, "to": body.role.value},
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Blocks login and revokes every live session of the user at once."""
    user = await _target(db, ctx, user_id)
    await _guard_last_admin(db, ctx, user)
    user.is_active = False
    await sessions.revoke_all(db, user.id)
    await audit.record(db, ctx, "user.deactivate", payload={"user_id": str(user_id)})
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reactivate", response_model=UserOut)
async def reactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    user = await _target(db, ctx, user_id)
    user.is_active = True
    await audit.record(db, ctx, "user.reactivate", payload={"user_id": str(user_id)})
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Removes an invitation that was never used. An account that has logged
    in has an audit history — deactivate it instead (409)."""
    user = await _target(db, ctx, user_id)
    if user.auth_subject_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "user has signed in; deactivate to keep the audit trail"
        )
    await db.delete(user)
    await audit.record(db, ctx, "user.remove", payload={"email": user.email})
    await db.commit()
