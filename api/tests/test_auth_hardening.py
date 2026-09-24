"""T-P34: server-side sessions, user management, OIDC nonce/email_verified,
WebSocket origin, auth rate limit, production defaults."""

import pytest
from sqlalchemy import select

from app.auth.deps import SESSION_COOKIE_NAME
from app.auth.oidc import OIDCIdentity
from app.models.enums import UserRole
from app.models.user_session import UserSession
from tests.factories import login_as, make_tenant, make_user


async def _admin(db_session, client):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    await login_as(client, admin)
    return tenant, admin


async def test_logout_revokes_the_session_server_side(client, db_session):
    await _admin(db_session, client)
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert (await client.get("/auth/me")).status_code == 200
    assert (await client.post("/auth/logout")).status_code == 200
    # The same cookie replayed after logout is dead (HQ-005).
    client.cookies.set(SESSION_COOKIE_NAME, token)
    assert (await client.get("/auth/me")).status_code == 401


async def test_token_without_a_session_row_is_rejected(client, db_session):
    import uuid

    from app.auth.session import issue_session_token

    tenant, admin = await _admin(db_session, client)
    forged = issue_session_token(admin.id, tenant.id, "admin", uuid.uuid4())
    client.cookies.set(SESSION_COOKIE_NAME, forged)
    assert (await client.get("/auth/me")).status_code == 401


async def test_role_change_applies_immediately_and_last_admin_is_kept(client, db_session):
    tenant, admin = await _admin(db_session, client)
    op = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    r = await client.patch(f"/users/{op.id}", json={"role": "viewer"})
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    # Demoted user's existing session is now a viewer (HQ-006).
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://t") as c2:
        await login_as(c2, op)
        assert (await c2.get("/users")).status_code == 403
    # The last active admin cannot be demoted by someone else… and nobody can
    # change their own account.
    assert (await client.patch(f"/users/{admin.id}", json={"role": "viewer"})).status_code == 409


async def test_deactivation_revokes_sessions_and_blocks_access(client, db_session):
    tenant, admin = await _admin(db_session, client)
    victim = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://t") as c2:
        await login_as(c2, victim)
        assert (await c2.get("/auth/me")).status_code == 200
        r = await client.post(f"/users/{victim.id}/deactivate")
        assert r.status_code == 200 and r.json()["is_active"] is False
        assert (await c2.get("/auth/me")).status_code == 401
    rows = (
        await db_session.execute(select(UserSession).where(UserSession.user_id == victim.id))
    ).scalars().all()
    assert rows and all(r.revoked_at is not None for r in rows)
    # Signed-in users are deactivated, not deleted (audit trail).
    assert (await client.delete(f"/users/{victim.id}")).status_code == 409
    invited = (await client.post("/users/invite", json={"email": "new@example.com"})).json()
    assert (await client.delete(f"/users/{invited['id']}")).status_code == 204


class _FakeOIDC:
    def __init__(self, identity):
        self.identity = identity
        self.seen_nonce = None

    def authorization_url(self, state, redirect_uri, nonce=None):
        return f"https://idp/auth?state={state}&nonce={nonce}"

    async def exchange_code(self, code, redirect_uri):
        return {"id_token": "x", "access_token": "y"}

    async def verify_id_token(self, id_token, access_token, nonce=None):
        self.seen_nonce = nonce
        return self.identity


async def _login_flow(client, fake):
    from app.routers.auth import get_oidc_client

    client._transport.app.dependency_overrides[get_oidc_client] = lambda: fake
    r = await client.get("/auth/login")
    assert "nonce=" in r.json()["authorization_url"]
    state = r.json()["authorization_url"].split("state=")[1].split("&")[0]
    return await client.post(f"/auth/callback?code=c&state={state}")


async def test_invite_link_requires_verified_email_and_nonce_is_passed(client, db_session):
    tenant = await make_tenant(db_session)
    await make_user(db_session, tenant, UserRole.viewer, email="inv@example.com")
    # Unlink the factory's subject so the email path is exercised.
    from app.models.user import User

    u = (await db_session.execute(select(User).where(User.email == "inv@example.com"))).scalar_one()
    u.auth_subject_id = None
    await db_session.commit()

    unverified = _FakeOIDC(OIDCIdentity(subject="s1", email="inv@example.com"))
    r = await _login_flow(client, unverified)
    assert r.status_code == 403, r.text
    assert unverified.seen_nonce  # nonce from the login cookie reached verification

    verified = _FakeOIDC(
        OIDCIdentity(subject="s1", email="inv@example.com", email_verified=True)
    )
    r = await _login_flow(client, verified)
    assert r.status_code == 200, r.text
    assert (await client.get("/auth/me")).json()["email"] == "inv@example.com"


async def test_auth_endpoints_are_rate_limited(client):
    from app.services import rate_limit

    rate_limit.reset()
    codes = [(await client.get("/auth/login")).status_code for _ in range(40)]
    rate_limit.reset()
    assert 429 in codes and codes[0] != 429


def test_production_is_the_default_and_refuses_dev_config(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("ACADIAHQ_ENV", raising=False)
    with pytest.raises(ValueError) as exc:
        Settings(_env_file=None)
    msg = str(exc.value)
    assert "public_base_url" in msg and "cors_allow_origins" in msg


def test_websocket_origin_is_checked():
    from app.routers.ws import _origin_allowed

    assert _origin_allowed("http://localhost:5173")
    assert not _origin_allowed("https://evil.example")
    assert not _origin_allowed(None)
