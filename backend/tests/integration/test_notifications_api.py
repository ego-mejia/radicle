"""Your notifications over REST and SSE (Folio 2.1, ADR 0038)."""

import asyncio
from collections.abc import AsyncIterator

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.api import notifications as api
from radicle.platform.db.models import OutboxEvent, User
from radicle.platform.services import events
from radicle.platform.services.notify_hub import Hub, _dsn
from tests.conftest import Team, run_jobs

URL = "/api/v1/me/notifications"


@events.resolver("test", "hello", label="Test hellos")
async def _hello(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    users = await db.scalars(select(User).where(User.handle.in_(event.payload["to"])))
    return [events.Notice(u.id, "test", event.payload["title"], link="/x") for u in users]


async def _hellos(db: AsyncSession, to: list[str], n: int) -> None:
    for i in range(n):
        await events.emit(db, "test", "hello", actor=None, payload={"to": to, "title": f"#{i}"})
    await run_jobs(db)


async def test_list_page_and_mark_read(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    await _hellos(db, [team.member.handle], 3)
    h = team.member.headers
    page = (await client.get(URL, params={"limit": 2}, headers=h)).json()
    assert [n["title"] for n in page["items"]] == ["#2", "#1"] and page["unread"] == 3
    assert page["items"][0]["params"] == {}  # a notice that sends none
    rest = (await client.get(URL, params={"cursor": page["next_cursor"]}, headers=h)).json()
    assert [n["title"] for n in rest["items"]] == ["#0"] and rest["next_cursor"] is None
    first = page["items"][0]["id"]
    r = await client.post(f"{URL}/read", headers=h, json={"ids": [first]})
    assert r.json() == {"marked": 1, "unread": 2}
    unread = (await client.get(URL, params={"unread_only": True}, headers=h)).json()
    assert first not in [n["id"] for n in unread["items"]]
    r = await client.post(f"{URL}/read", headers=h, json={})
    assert r.json() == {"marked": 2, "unread": 0}


async def test_nobody_else_sees_or_reads_yours(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await _hellos(db, [team.member.handle], 1)
    mine = (await client.get(URL, headers=team.member.headers)).json()["items"][0]["id"]
    other = team.viewer.headers
    assert (await client.get(URL, headers=other)).json()["items"] == []
    r = await client.post(f"{URL}/read", headers=other, json={"ids": [mine]})
    assert r.json()["marked"] == 0
    r = await client.get(URL, params={"cursor": mine}, headers=other)
    assert r.status_code == 422
    client.cookies.clear()  # the instance admin's session
    assert (await client.get(URL)).status_code == 401


async def test_preferences(client: AsyncClient, team: Team) -> None:
    h, prefs = team.member.headers, "/api/v1/me/notification-preferences"
    got = (await client.get(prefs, headers=h)).json()
    assert got["email_available"] is False
    hello = next(p for p in got["items"] if p["type"] == "hello")
    assert hello == {
        "app": "test",
        "type": "hello",
        "label": "Test hellos",
        "in_app": True,
        "email": True,
    }
    body = {"app": "test", "type": "hello", "channel": "in_app", "enabled": False}
    got = (await client.put(prefs, headers=h, json=body)).json()
    assert next(p for p in got["items"] if p["type"] == "hello")["in_app"] is False
    r = await client.put(prefs, headers=h, json=body | {"type": "nope"})
    assert r.status_code == 422 and "test.hello" in r.json()["detail"]


async def test_the_stream_signals_and_keeps_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "HEARTBEAT_SECONDS", 0.05)
    hub = Hub()
    async with hub.subscribe("u1", listen=False) as queue:
        chunks: AsyncIterator[str] = api.signals(queue)
        assert await anext(chunks) == "event: ready\ndata: {}\n\n"
        assert await anext(chunks) == ": ping\n\n"
        hub.publish("u1")
        hub.publish("someone-else")
        assert await anext(chunks) == "event: notification\ndata: {}\n\n"


async def test_the_hub_listens_to_postgres(database_url: str) -> None:
    hub = Hub()
    try:
        async with hub.subscribe("u2") as queue:
            sender = await asyncpg.connect(_dsn(database_url))
            try:
                await sender.execute(f"NOTIFY {events.CHANNEL}, 'u2'")
            finally:
                await sender.close()
            assert await asyncio.wait_for(queue.get(), timeout=5) == "u2"
    finally:
        await hub.close()
