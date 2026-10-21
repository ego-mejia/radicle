"""Real-time editing over WebSocket (Folio 2.2): /api/v1/folio/collab/{node_id}.

The Yjs protocol of `y-websocket`: binary sync and awareness messages. Sign in with the
session cookie (same origin only), `Authorization: Bearer`, or `?token=` for clients that
cannot send headers. Only people and agents who may edit the page connect; readers get
the published version over REST instead.
"""

import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, NodeKind
from radicle.folio.services import access, collab
from radicle.platform import authz
from radicle.platform.api.deps import SESSION_COOKIE
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.errors import ProblemError
from radicle.platform.services import auth

router = APIRouter(tags=["folio"])

# Close codes: 4401 not signed in, 4403 may not edit, 4404 no such page, 4429 room full.
UNAUTHORIZED, FORBIDDEN, NOT_FOUND, FULL = 4401, 4403, 4404, 4429


def _same_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if origin is None:
        return True  # not a browser: no cross-site risk
    expected = urlsplit(get_settings().base_url).netloc
    host = websocket.headers.get("host", "")
    return urlsplit(origin).netloc in {expected, host}


async def _user(db: AsyncSession, websocket: WebSocket) -> User | None:
    authorization = websocket.headers.get("authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    token = credentials.strip() if scheme.lower() == "bearer" else ""
    token = token or websocket.query_params.get("token", "")
    try:
        if token:
            return await auth.resolve_api_token(db, token)
        cookie = websocket.cookies.get(SESSION_COOKIE)
        if not cookie or not _same_origin(websocket):
            return None
        session = await auth.resolve_session(db, cookie, days=get_settings().session_days)
        return session.user if session else None
    except ProblemError:
        return None


@router.websocket("/collab/{node_id}")
async def collab_socket(websocket: WebSocket, node_id: uuid.UUID) -> None:
    async with collab.sessions() as db:
        user = await _user(db, websocket)
        if user is None:
            await websocket.close(code=UNAUTHORIZED, reason="Sign in or send an API token.")
            return
        allowed = await authz.authorize(db, user, "folio", "folio.read")
        node = await db.get(FolioNode, node_id)
        if not allowed.allowed or node is None or not await access.can_view(db, user, node_id):
            await websocket.close(code=NOT_FOUND, reason=f"Page {node_id} not found.")
            return
        if node.kind == NodeKind.folder or not await access.may_edit(db, user, node):
            await websocket.close(
                code=FORBIDDEN,
                reason="You can read this page but not edit it; open the published version.",
            )
            return
        room = await collab.rooms.open(db, node)
    if room.full:
        await websocket.close(
            code=FULL,
            reason=f"{collab.MAX_PEERS} people are editing this page already. Try again soon.",
        )
        return
    peer = collab.Peer(send=websocket.send_bytes, user=user)
    await websocket.accept()
    try:
        await room.join(peer)
    except collab.RoomFull as exc:
        await websocket.close(code=FULL, reason=exc.detail)
        return
    try:
        while True:
            await room.receive(peer, await websocket.receive_bytes())
    except WebSocketDisconnect:
        pass
    finally:
        await collab.rooms.leave(room, peer)
