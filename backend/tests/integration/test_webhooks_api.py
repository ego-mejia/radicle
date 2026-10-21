"""Webhooks over REST (Folio 5.5): instance admins manage them, ping them and read the
delivery log; nobody else can."""

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.services import safe_fetch, webhooks
from tests.conftest import Team, run_jobs

URL = "/api/v1/webhooks"
BODY = {"name": "CI", "url": "https://93.184.216.34/radicle", "events": []}


@pytest.fixture
def received(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    got: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        got.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return got


async def test_manage_ping_and_read_the_log(
    client: AsyncClient, db: AsyncSession, team: Team, received: list[httpx.Request]
) -> None:
    i = team.instance.headers
    r = await client.post(URL, headers=i, json=BODY)
    assert r.status_code == 201, r.text
    hook, secret = r.json(), r.json()["secret"]
    assert "secret" not in (await client.get(f"{URL}/{hook['id']}", headers=i)).json()
    names = [e["name"] for e in (await client.get(f"{URL}/events", headers=i)).json()]
    assert names == sorted(names)
    r = await client.post(f"{URL}/{hook['id']}/ping", headers=i)
    assert r.status_code == 202 and r.json()["event"] == "ping"
    await run_jobs(db)
    [request] = received
    assert webhooks.verify(secret, request.headers["radicle-signature"], request.content)
    log = (await client.get(f"{URL}/{hook['id']}/deliveries", headers=i)).json()
    assert log[0]["status"] == "sent" and log[0]["response_status"] == 204
    r = await client.post(f"{URL}/{hook['id']}/deliveries/{log[0]['id']}/redeliver", headers=i)
    assert r.status_code == 202
    new = (await client.post(f"{URL}/{hook['id']}/secret", headers=i)).json()["secret"]
    await run_jobs(db)
    assert webhooks.verify(new, received[1].headers["radicle-signature"], received[1].content)
    r = await client.put(f"{URL}/{hook['id']}", headers=i, json=BODY | {"active": False})
    assert r.json()["active"] is False
    assert [h["name"] for h in (await client.get(URL, headers=i)).json()] == ["CI"]
    assert (await client.delete(f"{URL}/{hook['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{URL}/{hook['id']}", headers=i)).status_code == 404


async def test_errors_say_how_to_fix(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.post(URL, headers=i, json=BODY | {"url": "http://10.0.0.1/hook"})
    assert r.status_code == 422 and "not a public address" in r.json()["detail"]
    r = await client.post(URL, headers=i, json=BODY | {"events": ["nope"]})
    assert r.status_code == 422 and "Valid ones" in r.json()["detail"]
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.get(f"{URL}/{missing}", headers=i)
    assert r.status_code == 404 and "GET /api/v1/webhooks" in r.json()["detail"]
    hook = (await client.post(URL, headers=i, json=BODY)).json()
    r = await client.post(f"{URL}/{hook['id']}/deliveries/999/redeliver", headers=i)
    assert r.status_code == 404


async def test_only_instance_admins(client: AsyncClient, team: Team) -> None:
    hook = (await client.post(URL, headers=team.instance.headers, json=BODY)).json()
    for actor in (team.admin, team.member):
        h = actor.headers
        assert (await client.get(URL, headers=h)).status_code == 403
        assert (await client.post(URL, headers=h, json=BODY)).status_code == 403
        assert (await client.get(f"{URL}/{hook['id']}/deliveries", headers=h)).status_code == 403
        assert (await client.delete(f"{URL}/{hook['id']}", headers=h)).status_code == 403
