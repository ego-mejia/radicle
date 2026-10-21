"""`/radicle` from Slack and Teams (Folio 5.4): signatures, who is asking, and slow
commands answered later on Slack's response_url."""

import base64
import json
import time
from urllib.parse import urlencode

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import Integration, IntegrationKind, User
from radicle.platform.services import chat_commands, integrations, safe_fetch
from radicle.platform.services.integrations import IntegrationData
from tests.conftest import Team, run_jobs

SIGNING = "slack-signing-secret"
TEAMS_SECRET = base64.b64encode(b"teams-shared-secret").decode()


async def _whoami(db: AsyncSession, user: User, text: str) -> str:
    return f"{user.handle}: {text}"


chat_commands.command("whoami", "says who you are")(_whoami)
chat_commands.command("later", "answers later", slow=True)(_whoami)


class Slack:
    def __init__(self) -> None:
        self.emails = {"U_FER": "admin@example.com", "U_NADIE": "nadie@otro.com"}
        self.replies: list[dict[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path == "/api/users.info":
            email = self.emails[body["user"]]
            return httpx.Response(200, json={"ok": True, "user": {"profile": {"email": email}}})
        self.replies.append(body)  # the response_url
        return httpx.Response(200, text="ok")


@pytest.fixture
def slack(monkeypatch: pytest.MonkeyPatch) -> Slack:
    got = Slack()

    async def resolve(host: str) -> list[str]:
        return ["54.230.1.1"]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(got))
    return got


async def _integration(db: AsyncSession, team: Team, kind: IntegrationKind) -> Integration:
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    creds = (
        {"bot_token": "xoxb-1", "signing_secret": SIGNING}
        if kind == IntegrationKind.slack
        else {"secret": TEAMS_SECRET}
    )
    made = await integrations.create(db, admin, IntegrationData(kind, "Acme", creds))
    await db.commit()  # a refused request rolls the session back
    return made


def _slack_request(text: str, user: str = "U_FER", stamp: int | None = None) -> dict:
    body = urlencode(
        {"user_id": user, "text": text, "response_url": "https://hooks.slack.com/commands/T1/x"}
    ).encode()
    ts = str(stamp or int(time.time()))
    signature = chat_commands.slack_signature(SIGNING, ts, body)
    headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    return {"content": body, "headers": headers}


async def test_slack_runs_commands_as_the_user_with_that_email(
    client: AsyncClient, db: AsyncSession, team: Team, slack: Slack
) -> None:
    hook = await _integration(db, team, IntegrationKind.slack)
    url = f"/api/v1/hooks/chat/{hook.id}/command"
    r = await client.post(url, **_slack_request("whoami hola"))
    assert r.status_code == 200, r.text
    assert r.json() == {"response_type": "ephemeral", "text": "fernando: hola"}
    r = await client.post(url, **_slack_request("later qué tal"))
    assert "On it: qué tal" in r.json()["text"]
    await run_jobs(db)
    assert slack.replies == [{"response_type": "ephemeral", "text": "fernando: qué tal"}]
    r = await client.post(url, **_slack_request("bailar"))
    assert "/radicle whoami" in r.json()["text"]
    r = await client.post(url, **_slack_request("whoami"))
    assert "Add what to whoami" in r.json()["text"]


async def test_signatures_and_unknown_integrations(
    client: AsyncClient, db: AsyncSession, team: Team, slack: Slack
) -> None:
    hook = await _integration(db, team, IntegrationKind.slack)
    url = f"/api/v1/hooks/chat/{hook.id}/command"
    forged = _slack_request("search x")
    forged["headers"]["X-Slack-Signature"] = "v0=" + "0" * 64
    assert (await client.post(url, **forged)).status_code == 401
    old = _slack_request("search x", stamp=int(time.time()) - 3600)
    r = await client.post(url, **old)
    assert r.status_code == 401 and "too old" in r.json()["detail"]
    missing = "/api/v1/hooks/chat/00000000-0000-0000-0000-000000000000/command"
    assert (await client.post(missing, **_slack_request("search x"))).status_code == 404


async def test_a_stranger_links_their_account_first(
    client: AsyncClient,
    db: AsyncSession,
    team: Team,
    slack: Slack,
) -> None:
    hook = await _integration(db, team, IntegrationKind.slack)
    url = f"/api/v1/hooks/chat/{hook.id}/command"
    r = await client.post(url, **_slack_request("whoami x", user="U_NADIE"))
    text = r.json()["text"]
    assert "couldn't find your Radicle account" in text
    token = text.split("token=", 1)[1]
    r = await client.post(
        "/api/v1/integrations/link", headers=team.member.headers, json={"token": token}
    )
    assert r.status_code == 200 and r.json() == {"integration": "Acme"}
    r = await client.post(url, **_slack_request("whoami x", user="U_NADIE"))
    assert r.json()["text"] == f"{team.member.handle}: x"
    r = await client.post(
        "/api/v1/integrations/link", headers=team.member.headers, json={"token": "nope"}
    )
    assert r.status_code == 422 and "isn't valid" in r.json()["detail"]
    r = await client.post(
        "/api/v1/integrations/link", headers=team.agent.headers, json={"token": token}
    )
    assert r.status_code == 403


async def test_teams_asks_to_link_then_answers(
    client: AsyncClient,
    db: AsyncSession,
    team: Team,
) -> None:
    hook = await _integration(db, team, IntegrationKind.teams)
    url = f"/api/v1/hooks/chat/{hook.id}/command"

    def activity(text: str) -> dict:
        body = json.dumps({"type": "message", "text": text, "from": {"aadObjectId": "aad-1"}})
        content = body.encode()
        auth = chat_commands.teams_signature(TEAMS_SECRET, content)
        return {"content": content, "headers": {"Authorization": auth}}

    r = await client.post(url, **activity("<at>Radicle</at> whoami hola"))
    assert r.status_code == 200 and "Connect your Radicle account" in r.json()["text"]
    token = r.json()["text"].split("token=", 1)[1]
    await client.post(
        "/api/v1/integrations/link", headers=team.member.headers, json={"token": token}
    )
    r = await client.post(url, **activity("<at>Radicle</at> whoami hola"))
    assert r.json() == {"type": "message", "text": f"{team.member.handle}: hola"}
    bad = activity("search x") | {"headers": {"Authorization": "HMAC bad"}}
    assert (await client.post(url, **bad)).status_code == 401
