"""The read-only iCal feed of a calendar (Folio 5.8), outside /api and without signing in:
the token in the link is the access. Rotating it in the calendar's settings cuts it off."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

from radicle.folio.services import calendars, ical
from radicle.platform.api.deps import Db

router = APIRouter(tags=["folio"])


@router.get("/ical/{token}.ics", include_in_schema=False)
async def calendar_feed(token: str, request: Request, db: Db) -> Response:
    calendar, agenda = await calendars.feed(db, token)
    body = ical.render(
        calendar, agenda, host=request.url.hostname or "radicle", now=datetime.now(UTC)
    )
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="calendar.ics"',
            "Cache-Control": "private, max-age=300",
            "X-Robots-Tag": "noindex",
        },
    )
