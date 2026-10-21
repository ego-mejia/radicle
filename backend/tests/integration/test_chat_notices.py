"""Notices to Slack and Teams (Folio 5.4). Acceptance: publishing in the Anuncios space
posts a notice to Slack."""

import base64
import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import DeliveryStatus, IntegrationKind, IntegrationNotice, User
from radicle.platform.services import integrations, safe_fetch
from radicle.platform.services.integrations import IntegrationData, Route
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish

SLACK = {"bot_token": "xoxb-1-2-abc", "signing_secret": "s3cr3t"}
TEAMS_HOOK = "https://93.184.216.34/webhookb2/abc"


class Chat:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.slack_ok = True

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.posts.append((request.headers["host"] + request.url.path, json.loads(request.content)))
        if request.headers["host"] == "slack.com":
            body = {"ok": True} if self.slack_ok else {"ok": False, "error": "channel_not_found"}
            return httpx.Response(200, json=body)
        return httpx.Response(200, text="1")


@pytest.fixture
def chat(monkeypatch: pytest.MonkeyPatch) -> Chat:
    got = Chat()

    async def resolve(host: str) -> list[str]:
        return ["54.230.1.1"]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(got))
    return got


async def _setup(client: AsyncClient, db: AsyncSession, team: Team) -> str:
    i = team.instance.headers
    for key, name in (("anuncios", "Anuncios"), ("eng", "Ingeniería")):
        await client.post(f"{API}/spaces", headers=i, json={"key": key, "name": name})
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    only_news = Route("C0ANUNCIOS", ["page.published"], {"space": "anuncios"})
    await integrations.create(
        db, admin, IntegrationData(IntegrationKind.slack, "Acme", SLACK, [only_news])
    )
    secret = base64.b64encode(b"x").decode()
    await integrations.create(
        db,
        admin,
        IntegrationData(
            IntegrationKind.teams, "Acme Teams", {"secret": secret}, [Route(TEAMS_HOOK)]
        ),
    )
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "anuncios", "kind": "page", "title": "Q4"}
    )
    return str(r.json()["id"])


async def test_acceptance_publishing_in_anuncios_tells_slack(
    client: AsyncClient, db: AsyncSession, team: Team, chat: Chat
) -> None:
    page = await _setup(client, db, team)
    await publish(client, team, page)
    await run_jobs(db)
    slack = [body for where, body in chat.posts if where == "slack.com/api/chat.postMessage"]
    [message] = slack
    link = f"http://localhost:8000/folio/p/{page}-q4"
    assert set(message) == {"channel", "text"} and message["channel"] == "C0ANUNCIOS"
    assert str(message["text"]).endswith(f"published “Q4” in anuncios\n<{link}>")
    teams = [body for where, body in chat.posts if where == "93.184.216.34/webhookb2/abc"]
    assert teams and teams[0]["@type"] == "MessageCard"
    # The Slack route asks only for page.published in anuncios: elsewhere stays quiet.
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Infra"}
    )
    await publish(client, team, str(r.json()["id"]))
    await run_jobs(db)
    assert len([w for w, _ in chat.posts if w.startswith("slack.com")]) == 1


async def test_slack_errors_retry_then_stay_failed(
    client: AsyncClient, db: AsyncSession, team: Team, chat: Chat
) -> None:
    chat.slack_ok = False
    await publish(client, team, await _setup(client, db, team))
    await run_jobs(db)
    notice = await db.scalar(
        select(IntegrationNotice).where(IntegrationNotice.text.like("%anuncios%<%"))
    )
    assert notice is not None and notice.status == DeliveryStatus.failed
    assert notice.attempts == 3 and "channel_not_found" in (notice.last_error or "")
