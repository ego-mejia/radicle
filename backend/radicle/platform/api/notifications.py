"""Your notifications (ADR 0038): the bell's list, marking read, the live stream and your
preferences per type and channel."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import Field

from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import Channel
from radicle.platform.services import events
from radicle.platform.services import notifications as service
from radicle.platform.services.notify_hub import hub

router = APIRouter(prefix="/me", tags=["notifications"])
HEARTBEAT_SECONDS = 25


class NotificationOut(Output):
    id: uuid.UUID
    app: str
    type: str
    title: str
    body: str
    link: str | None
    actor_id: uuid.UUID | None
    read: bool
    created_at: UtcDatetime


class NotificationsPage(Output):
    items: list[NotificationOut]
    next_cursor: str | None = None
    unread: int


class ReadIn(Input):
    ids: list[uuid.UUID] | None = Field(default=None, description="Leave out to mark all read")


class ReadOut(Output):
    marked: int
    unread: int


class PreferenceOut(Output):
    app: str
    type: str
    label: str
    in_app: bool
    email: bool


class PreferencesOut(Output):
    email_available: bool = Field(description="False until an admin configures SMTP")
    items: list[PreferenceOut]


class PreferenceIn(Input):
    app: str
    type: str
    channel: Literal["in_app", "email"]
    enabled: bool


@router.get("/notifications", response_model=NotificationsPage)
async def list_notifications(
    principal: CurrentPrincipal,
    db: Db,
    unread_only: bool = False,
    cursor: uuid.UUID | None = None,
    limit: int = Query(default=30, ge=1, le=service.MAX_LIMIT),
) -> NotificationsPage:
    """Newest first, with how many are unread."""
    user = principal.user
    rows = await service.list_for(db, user, unread_only=unread_only, before=cursor, limit=limit)
    return NotificationsPage(
        items=[
            NotificationOut(
                id=n.id,
                app=n.app,
                type=n.type,
                title=n.title,
                body=n.body,
                link=n.link,
                actor_id=n.actor_id,
                read=n.read_at is not None,
                created_at=n.created_at,
            )
            for n in rows
        ],
        next_cursor=str(rows[-1].id) if len(rows) == limit else None,
        unread=await service.unread_count(db, user),
    )


@router.post("/notifications/read", response_model=ReadOut)
async def read_notifications(body: ReadIn, principal: CurrentPrincipal, db: Db) -> ReadOut:
    marked = await service.mark_read(db, principal.user, body.ids)
    return ReadOut(marked=marked, unread=await service.unread_count(db, principal.user))


async def signals(
    queue: "asyncio.Queue[str]", request: Request | None = None
) -> AsyncIterator[str]:
    """Server-sent events: `ready`, then `notification` each time one arrives (the client
    refetches the list), with a comment every 25 s to keep proxies from closing it."""
    yield "event: ready\ndata: {}\n\n"
    while request is None or not await request.is_disconnected():
        try:
            await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
        except TimeoutError:
            yield ": ping\n\n"
            continue
        yield "event: notification\ndata: {}\n\n"


@router.get("/notifications/stream")
async def stream(principal: CurrentPrincipal, request: Request) -> StreamingResponse:
    """Live signals for the bell (text/event-stream)."""
    user_id = str(principal.user.id)

    async def body() -> AsyncIterator[str]:
        async with hub.subscribe(user_id) as queue:
            async for chunk in signals(queue, request):
                yield chunk

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(body(), media_type="text/event-stream", headers=headers)


async def _preferences(db: Db, principal: CurrentPrincipal) -> PreferencesOut:
    prefs = await service.preferences(db, principal.user)
    return PreferencesOut(
        email_available=events.email_enabled(),
        items=[PreferenceOut(**p.__dict__) for p in prefs],
    )


@router.get("/notification-preferences", response_model=PreferencesOut)
async def get_preferences(principal: CurrentPrincipal, db: Db) -> PreferencesOut:
    """Every notification type with whether it reaches you in the app and by email."""
    return await _preferences(db, principal)


@router.put("/notification-preferences", response_model=PreferencesOut)
async def put_preference(body: PreferenceIn, principal: CurrentPrincipal, db: Db) -> PreferencesOut:
    await service.set_preference(
        db, principal.user, body.app, body.type, Channel(body.channel), body.enabled
    )
    return await _preferences(db, principal)
