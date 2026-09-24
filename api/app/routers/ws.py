from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.deps import SESSION_COOKIE_NAME
from app.config import get_settings
from app.db.base import get_session_factory
from app.services import sessions
from app.services.device_status_broadcast import subscribers


def _origin_allowed(origin: str | None) -> bool:
    """T-P34 (HQ-009): cross-site WebSocket hijacking defence — the browser
    always sends Origin on a WebSocket handshake; only HQ's own origins may
    open one with the session cookie."""
    if not origin:
        return False
    settings = get_settings()
    allowed = set(settings.cors_allow_origins)
    if settings.public_base_url:
        allowed.add(settings.public_base_url.rstrip("/"))
    return origin.rstrip("/") in allowed

router = APIRouter(tags=["ws"])


@router.websocket("/ws/devices")
async def ws_devices(websocket: WebSocket) -> None:
    if not _origin_allowed(websocket.headers.get("origin")):
        await websocket.close(code=4403)
        return
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        await websocket.close(code=4401)
        return
    async with get_session_factory()() as db:
        ctx = await sessions.resolve(db, token)
    if ctx is None:
        await websocket.close(code=4401)
        return

    tenant_id = ctx.tenant_id
    await websocket.accept()
    subscribers.subscribe(tenant_id, websocket)
    try:
        while True:
            # No client->server messages expected; just keep the socket open
            # and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        subscribers.unsubscribe(tenant_id, websocket)
