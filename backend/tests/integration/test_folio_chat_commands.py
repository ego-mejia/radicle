"""Folio's `/radicle` commands (Folio 5.4). Acceptance: `/radicle ask` in Slack answers with
citations, as the Radicle user behind the Slack account."""

import json
import time
from urllib.parse import urlencode

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.chat import FolioChatSession
from radicle.folio.services import chat
from radicle.platform.db.models import IntegrationKind, User
from radicle.platform.services import chat_commands, integrations, safe_fetch
from radicle.platform.services.integrations import IntegrationData
from tests.conftest import Team, run_jobs
from tests.integration.folio_chat_helpers import docs, model  # noqa: F401  (fixtures)

SIGNING = "slack-signing-secret"


@pytest.fixture
def replies(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    got: list[dict[str, str]] = []

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/users.info":
            profile = {"email": "admin@example.com"}
            return httpx.Response(200, json={"ok": True, "user": {"profile": profile}})
        got.append(json.loads(request.content))
        return httpx.Response(200, text="ok")

    async def resolve(host: str) -> list[str]:
        return ["54.230.1.1"]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return got


async def _slash(client: AsyncClient, db: AsyncSession, team: Team, text: str) -> dict:
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    found = await integrations.list_all(db)
    if not found:
        creds = {"bot_token": "xoxb-1", "signing_secret": SIGNING}
        found = [
            await integrations.create(db, admin, IntegrationData(IntegrationKind.slack, "A", creds))
        ]
    body = urlencode(
        {"user_id": "U1", "text": text, "response_url": "https://hooks.slack.com/commands/1"}
    ).encode()
    ts = str(int(time.time()))
    headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": chat_commands.slack_signature(SIGNING, ts, body),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    r = await client.post(
        f"/api/v1/hooks/chat/{found[0].id}/command", content=body, headers=headers
    )
    assert r.status_code == 200, r.text
    return dict(r.json())


async def test_acceptance_ask_answers_with_citations(
    client: AsyncClient,
    db: AsyncSession,
    team: Team,
    replies: list[dict[str, str]],
    docs: dict,  # noqa: F811
    model: list[dict],  # noqa: F811
) -> None:
    first = await _slash(client, db, team, "ask ¿cómo conecto un agente?")
    assert first["text"] == "On it: ¿cómo conecto un agente?"
    await run_jobs(db)
    [reply] = replies
    assert reply["text"].startswith("Ve a Admin, Agentes [1].")
    guide = f"http://localhost:8000/folio/p/{docs['guide']}"
    assert f"[1] Conecta un agente a Radicle: {guide}" in reply["text"]
    session = await db.scalar(select(FolioChatSession))
    fernando = await db.scalar(select(User).where(User.handle == "fernando"))
    assert session is not None and fernando is not None and session.user_id == fernando.id


async def test_search_gives_the_top_five(
    client: AsyncClient,
    db: AsyncSession,
    team: Team,
    replies: list[dict[str, str]],
    docs: dict,  # noqa: F811
) -> None:
    text = (await _slash(client, db, team, "search agente"))["text"]
    assert text.startswith("• Conecta un agente a Radicle (docs): http://localhost:8000/folio/p/")
    text = (await _slash(client, db, team, "search zzzqqq"))["text"]
    assert text == "Nothing in the docs matches “zzzqqq”."
    # Without a chat model, ask says so instead of failing.
    await _slash(client, db, team, "ask hola")
    await run_jobs(db)
    assert replies[-1]["text"] == chat.OFF["no_provider"]
