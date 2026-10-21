"""Slack and Teams over REST (Folio 5.4): instance admins set them up and test a channel;
secrets never come back; nobody else can."""

import base64

import httpx
import pytest
from httpx import AsyncClient

from radicle.platform.services import safe_fetch
from tests.conftest import Team

URL = "/api/v1/integrations"
TEAMS = {
    "kind": "teams",
    "name": "Acme Teams",
    "credentials": {"secret": base64.b64encode(b"shared").decode()},
    "notices": [{"channel": "https://93.184.216.34/webhookb2/abc", "events": ["page.published"]}],
}


@pytest.fixture
def teams_answers(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    answers: list[int] = []

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(answers.pop(0) if answers else 200, text="1")

    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return answers


async def test_set_up_test_and_remove(
    client: AsyncClient, team: Team, teams_answers: list[int]
) -> None:
    i = team.instance.headers
    r = await client.post(URL, headers=i, json=TEAMS)
    assert r.status_code == 201, r.text
    made = r.json()
    assert made["notices"][0]["channel"] == "93.184.216.34/…"
    assert made["command_url"].endswith(f"/api/v1/hooks/chat/{made['id']}/command")
    assert made["events_url"] is None  # only Slack previews links
    assert "shared" not in r.text and "webhookb2" not in r.text
    r = await client.post(f"{URL}/{made['id']}/test", headers=i, json={"route": 0})
    assert r.json() == {"ok": True, "message": "Posted a test message."}
    teams_answers.append(404)
    r = await client.post(f"{URL}/{made['id']}/test", headers=i, json={"route": 0})
    assert r.json() == {"ok": False, "message": "Teams answered HTTP 404."}
    keep = TEAMS | {"name": "Acme", "credentials": None, "notices": None}
    r = await client.put(f"{URL}/{made['id']}", headers=i, json=keep)
    assert r.json()["name"] == "Acme" and len(r.json()["notices"]) == 1
    assert [x["name"] for x in (await client.get(URL, headers=i)).json()] == ["Acme"]
    assert (await client.delete(f"{URL}/{made['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{URL}/{made['id']}", headers=i)).status_code == 404


async def test_errors_say_how_to_fix(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.post(URL, headers=i, json=TEAMS | {"kind": "slack"})
    assert r.status_code == 422 and "xoxb-" in r.json()["detail"]
    made = (await client.post(URL, headers=i, json=TEAMS)).json()
    r = await client.put(f"{URL}/{made['id']}", headers=i, json=TEAMS | {"kind": "slack"})
    assert r.status_code == 422 and "can't change kind" in r.json()["detail"]
    r = await client.post(f"{URL}/{made['id']}/test", headers=i, json={"route": 3})
    assert r.status_code == 422 and "use 0 to 0" in r.json()["detail"]
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.get(f"{URL}/{missing}", headers=i)
    assert r.status_code == 404 and "GET /api/v1/integrations" in r.json()["detail"]


async def test_only_instance_admins(client: AsyncClient, team: Team) -> None:
    made = (await client.post(URL, headers=team.instance.headers, json=TEAMS)).json()
    for actor in (team.admin, team.member):
        h = actor.headers
        assert (await client.get(URL, headers=h)).status_code == 403
        assert (await client.post(URL, headers=h, json=TEAMS)).status_code == 403
        assert (await client.get(f"{URL}/{made['id']}", headers=h)).status_code == 403
        r = await client.post(f"{URL}/{made['id']}/test", headers=h, json={"route": 0})
        assert r.status_code == 403
