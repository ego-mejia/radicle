"""Calendars and their events over REST (Folio 5.8); the iCal feed: test_folio_ical_feed.py."""

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


async def test_events_over_rest(client: AsyncClient, db: AsyncSession, board: Team) -> None:
    cal = await _calendar(client, db, board)
    a, m, v = board.admin.headers, board.member.headers, board.viewer.headers
    body = {"title": "Demo", "start_at": "2026-12-03T10:00:00Z", "end_at": "2026-12-03T11:00:00Z"}
    eid = (await client.post(f"{API}/calendars/{cal['id']}/events", headers=a, json=body)).json()[
        "id"
    ]
    params = {"start": "2026-12-01T00:00:00Z", "end": "2027-01-01T00:00:00Z"}
    r = await client.get(f"{API}/calendars/{cal['id']}/events", headers=v, params=params)
    assert r.status_code == 200, r.text
    assert [e["title"] for e in r.json()["events"]] == ["Demo"]
    assert r.json()["events"][0]["can_edit"] is False
    assert [(x["project"], x["name"], x["due"]) for x in r.json()["milestones"]] == [
        ("PA", "V1", "2026-12-15")
    ]
    url = f"{API}/calendars/{cal['id']}/events/{eid}"
    assert (await client.patch(url, headers=m, json={"title": "Mía"})).status_code == 403
    r = await client.patch(url, headers=a, json={"title": "Demo final", "category": "oncall"})
    assert r.json()["title"] == "Demo final" and r.json()["category"] == "oncall"
    assert (await client.delete(url, headers=a)).status_code == 204
    assert (await client.delete(url, headers=a)).status_code == 404

    listed = await client.get(f"{API}/calendars", headers=v, params={"space": "eng"})
    assert [c["name"] for c in listed.json()["items"]] == ["Releases"]
    assert listed.json()["items"][0]["can_manage"] is False
    everywhere = await client.get(f"{API}/calendars", headers=v)
    assert [c["space"] for c in everywhere.json()["items"]] == ["eng"]
    nothing = await client.get(f"{API}/calendars", headers=board.outsider.headers)
    assert nothing.json()["items"] == []
    i = board.instance.headers
    r = await client.patch(f"{API}/calendars/{cal['id']}", headers=i, json={"name": "Lanzamientos"})
    assert r.json()["name"] == "Lanzamientos"
    r = await client.post(f"{API}/calendars/{cal['id']}/ical-token", headers=i)
    assert r.json()["ical_path"] != cal["ical_path"]
    assert (await client.get(f"{API}/calendars/{cal['id']}", headers=v)).status_code == 200
    assert (await client.delete(f"{API}/calendars/{cal['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{API}/calendars/{cal['id']}", headers=v)).status_code == 404


async def test_errors_and_permissions(client: AsyncClient, db: AsyncSession, board: Team) -> None:
    cal = await _calendar(client, db, board)
    a, v, o = board.admin.headers, board.viewer.headers, board.outsider.headers
    i = board.instance.headers
    # Only space admins manage calendars; a space you can't see is a 404.
    body = {"space": "eng", "name": "Otro"}
    assert (await client.post(f"{API}/calendars", headers=a, json=body)).status_code == 403
    assert (await client.post(f"{API}/calendars", headers=o, json=body)).status_code == 404
    r = await client.post(f"{API}/calendars", headers=i, json=body | {"color": "pink"})
    assert r.status_code == 422
    r = await client.post(f"{API}/calendars", headers=i, json=body | {"docket_projects": ["ZZ"]})
    assert r.status_code == 422 and "ZZ" in r.json()["detail"]
    assert (await client.get(f"{API}/calendars/{cal['id']}", headers=o)).status_code == 404
    assert (
        await client.patch(f"{API}/calendars/{cal['id']}", headers=a, json={"name": "x"})
    ).status_code == 403
    assert (
        await client.post(f"{API}/calendars/{cal['id']}/ical-token", headers=a)
    ).status_code == 403
    assert (await client.delete(f"{API}/calendars/{cal['id']}", headers=a)).status_code == 403
    # Readers don't add events; bad ranges and dates say what to fix.
    event = {"title": "X", "start_at": "2026-12-03T10:00:00Z", "end_at": "2026-12-03T09:00:00Z"}
    url = f"{API}/calendars/{cal['id']}/events"
    assert (await client.post(url, headers=v, json=event)).status_code == 403
    r = await client.post(url, headers=a, json=event)
    assert r.status_code == 422 and "before" in r.json()["detail"]
    params = {"start": "2026-12-01T00:00:00Z", "end": "2028-02-01T00:00:00Z"}
    r = await client.get(url, headers=v, params=params)
    assert r.status_code == 422 and "400 days" in r.json()["detail"]
    assert (await client.get(url, headers=o, params=params)).status_code == 404
