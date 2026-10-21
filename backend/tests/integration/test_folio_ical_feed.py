"""A calendar's iCal feed (Folio 5.8). Acceptance: I subscribe to the releases calendar
from Google Calendar and see the releases."""

from datetime import UTC, datetime, timedelta

import icalendar
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team
from tests.integration.folio_calendar_helpers import eng_space
from tests.integration.folio_helpers import API


async def _calendar(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    await eng_space(client, db, team)
    body = {"space": "eng", "name": "Releases", "color": "green", "docket_projects": ["pa"]}
    r = await client.post(f"{API}/calendars", headers=team.instance.headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_acceptance_subscribe_to_the_releases(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    cal = await _calendar(client, db, board)
    assert cal["can_manage"] and cal["docket_projects"] == ["PA"]
    soon = datetime.now(UTC).replace(microsecond=0) + timedelta(days=7)
    event = {
        "title": "Release 2.0; final, by @ana",
        "description": "Notas\nen dos líneas",
        "start_at": soon.isoformat(),
        "end_at": (soon + timedelta(hours=1)).isoformat(),
        "category": "release",
        "people": ["luis"],
    }
    r = await client.post(
        f"{API}/calendars/{cal['id']}/events", headers=board.admin.headers, json=event
    )
    assert r.status_code == 201, r.text
    assert r.json()["people"] == ["luis"] and r.json()["created_by"] == "ana"
    day = {"title": "Congelamiento", "start_at": soon.isoformat(), "end_at": soon.isoformat()}
    r = await client.post(
        f"{API}/calendars/{cal['id']}/events",
        headers=board.member.headers,
        json=day | {"all_day": True, "category": "other"},
    )
    assert r.status_code == 201, r.text

    r = await client.get(cal["ical_path"])  # no session, no token: the link is the access
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/calendar")
    assert r.headers["x-robots-tag"] == "noindex"
    assert all(len(line.encode()) <= 75 for line in r.text.split("\r\n"))
    parsed = icalendar.Calendar.from_ical(r.content)
    assert str(parsed["X-WR-CALNAME"]) == "Releases"
    by_title = {str(e["SUMMARY"]): e for e in parsed.walk("VEVENT")}
    assert set(by_title) == {"Release 2.0; final, by @ana", "Congelamiento", "PA · V1"}
    release = by_title["Release 2.0; final, by @ana"]
    assert release.decoded("DTSTART") == soon
    assert str(release["DESCRIPTION"]) == "Notas\nen dos líneas"
    assert by_title["Congelamiento"].decoded("DTSTART") == soon.date()
    assert str(by_title["PA · V1"].decoded("DTSTART")) == "2026-12-15"


async def test_rotating_or_deleting_cuts_the_feed_off(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    cal = await _calendar(client, db, board)
    i = board.instance.headers
    assert (await client.get(cal["ical_path"])).status_code == 200
    r = await client.post(f"{API}/calendars/{cal['id']}/ical-token", headers=i)
    assert (await client.get(cal["ical_path"])).status_code == 404
    assert (await client.get(r.json()["ical_path"])).status_code == 200
    assert (await client.delete(f"{API}/calendars/{cal['id']}", headers=i)).status_code == 204
    assert (await client.get(r.json()["ical_path"])).status_code == 404
    assert (await client.get("/ical/nope.ics")).status_code == 404
