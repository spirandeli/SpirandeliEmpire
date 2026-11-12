"""SpirandeliEmpire OS 3.1 — Real-Time WebSocket Streaming Endpoint"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.events.manager import event_system
from app.auth.security import decode_access_token
from app.auth.dependencies import ACCESS_COOKIE_NAME
from app.database.session import AsyncSessionLocal
from app.database.models import UserSessionModel

router = APIRouter()


@router.websocket("/events")
async def websocket_events_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
):
    raw_token = token or websocket.cookies.get(ACCESS_COOKIE_NAME)
    payload = decode_access_token(raw_token) if raw_token else None
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return

    sid = payload.get("sid")
    if sid:
        async with AsyncSessionLocal() as session:
            sess = await session.get(UserSessionModel, sid)
            if not sess or sess.is_revoked or (sess.expires_at and sess.expires_at.replace(tzinfo=None) < datetime.utcnow()):
                await websocket.close(code=4401)
                return

    await event_system.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event_type": "pong"}')
    except WebSocketDisconnect:
        await event_system.disconnect(websocket)
    except Exception:
        await event_system.disconnect(websocket)
