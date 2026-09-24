import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import SESSION_COOKIE_NAME, get_current_context
from app.auth.oidc import OIDCClient, OIDCError
from app.config import get_settings
from app.db.deps import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.services import audit, rate_limit, sessions
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/auth", tags=["auth"])
_STATE_COOKIE = "acadiahq_oidc_state"
_NONCE_COOKIE = "acadiahq_oidc_nonce"


def get_oidc_client() -> OIDCClient:
    return OIDCClient()


def _redirect_uri(request: Request) -> str:
    """The OIDC redirect_uri. Production (T-P34, HQ-003/004): always
    `public_base_url` — never derived from the client-controllable Host /
    X-Forwarded-* headers, and always https (the config refuses anything
    else). Dev/test: the browser's own origin as Vite's dev proxy forwards it
    (xfwd), so LAN/mDNS hostnames keep working.

    Must return the same value on /auth/login and /auth/callback.
    """
    settings = get_settings()
    if settings.public_base_url:
        return f"{settings.public_base_url.rstrip('/')}/auth/callback"
    host = request.headers.get("x-forwarded-host") or request.headers.get(
        "host", settings.oidc_redirect_fallback_host
    )
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}/auth/callback"


def _rate_limited(request: Request) -> None:
    rate_limit.check("auth", request, get_settings().auth_rate_limit_per_minute)


@router.get("/login", dependencies=[Depends(_rate_limited)])
async def login(
    request: Request, response: Response, oidc: OIDCClient = Depends(get_oidc_client)
):
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    url = oidc.authorization_url(state, _redirect_uri(request), nonce=nonce)
    secure = get_settings().env not in ("dev", "test")
    response.set_cookie(
        _STATE_COOKIE, state, httponly=True, samesite="lax", max_age=600, secure=secure
    )
    response.set_cookie(
        _NONCE_COOKIE, nonce, httponly=True, samesite="lax", max_age=600, secure=secure
    )
    return {"authorization_url": url}


@router.post("/callback", dependencies=[Depends(_rate_limited)])
async def callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    oidc: OIDCClient = Depends(get_oidc_client),
):
    expected_state = request.cookies.get(_STATE_COOKIE)
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid oidc state")
    nonce = request.cookies.get(_NONCE_COOKIE)
    if not nonce:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing oidc nonce")

    try:
        tokens = await oidc.exchange_code(code, _redirect_uri(request))
        identity = await oidc.verify_id_token(
            tokens["id_token"], tokens["access_token"], nonce=nonce
        )
    except OIDCError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    settings = get_settings()
    user = (
        await db.execute(select(User).where(User.auth_subject_id == identity.subject))
    ).scalar_one_or_none()

    if user is None:
        # First login for this identity: match a pre-invited, not-yet-linked
        # user record by email. T-P34 (HQ-001): only when the IdP asserts the
        # email is verified — otherwise anyone who can register that address
        # at the IdP takes over the invitation.
        if settings.oidc_require_email_verified and not identity.email_verified:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "email not verified at the identity provider"
            )
        user = (
            await db.execute(
                select(User).where(User.email == identity.email, User.auth_subject_id.is_(None))
            )
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "no invited user found for this email")
        user.auth_subject_id = identity.subject
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user is deactivated")

    session_token = await sessions.create_session(db, user)
    ctx = TenantContext(tenant_id=user.tenant_id, user_id=user.id, role=user.role.value)
    await audit.record(db, ctx, "auth.login")
    await db.commit()

    response.delete_cookie(_STATE_COOKIE)
    response.delete_cookie(_NONCE_COOKIE)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        secure=settings.env not in ("dev", "test"),
        max_age=settings.session_ttl_seconds,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_context),
):
    """T-P34 (HQ-005): revoke the server-side session — the cookie is dead
    everywhere, not just deleted from this browser."""
    if ctx.sid is not None:
        await sessions.revoke(db, ctx.sid)
    await audit.record(db, ctx, "auth.logout")
    await db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_context),
):
    user = (await db.execute(select(User).where(User.id == ctx.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session user no longer exists")
    return UserOut.model_validate(user)
