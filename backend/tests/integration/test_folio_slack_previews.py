"""Previews of Folio links pasted in Slack (Folio 5.4): only when the person who pasted
the link can see the page through their linked Radicle account."""

import json
import time

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import IntegrationKind, User
from radicle.platform.services import chat_commands, integrations, safe_fetch
from radicle.platform.services.integrations import IntegrationData
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, METADATA, publish

SIGNING = "slack-signing-secret"
BASE = "http://localhost:8000"


@pytest.fixture
def unfurls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    got: list[dict] = []

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path == "/api/users.info":
            email = {"U_LUIS": "luis@example.com", "U_X": "x@otro.com"}[body["user"]]
            return httpx.Response(200, json={"ok": True, "user": {"profile": {"email": email}}})
        got.append(body)
        return httpx.Response(200, json={"ok": True})

    async def resolve(host: str) -> list[str]:
        return ["54.230.1.1"]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return got


async def _send(client: AsyncClient, url: str, doc: dict) -> httpx.Response:
    body = json.dumps(doc).encode()
    ts = str(int(time.time()))
    headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": chat_commands.slack_signature(SIGNING, ts, body),
        "Content-Type": "application/json",
    }
    return await client.post(url, content=body, headers=headers)


def _shared(user: str, *urls: str) -> dict:
    links = [{"url": u, "domain": "localhost"} for u in urls]
    event = {
        "type": "link_shared",
        "user": user,
        "channel": "C1",
        "message_ts": "1.2",
        "links": links,
    }
    return {"type": "event_callback", "event": event}


async def test_previews_only_pages_the_paster_can_see(
    client: AsyncClient, db: AsyncSession, team: Team, unfurls: list[dict]
) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    pages = []
    for title in ("Guía", "Secreto"):
        r = await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
        )
        pages.append(r.json())
        await publish(client, team, r.json()["id"])
    body = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    await client.put(f"{API}/nodes/{pages[1]['id']}/restrictions", headers=i, json=body)
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    creds = {"bot_token": "xoxb-1", "signing_secret": SIGNING}
    hook = await integrations.create(db, admin, IntegrationData(IntegrationKind.slack, "A", creds))
    await db.commit()
    url = f"/api/v1/hooks/chat/{hook.id}/events"
    r = await _send(client, url, {"type": "url_verification", "challenge": "abc"})
    assert r.json() == {"challenge": "abc"}
    guide, secret = (f"{BASE}/folio/p/{p['id']}-x" for p in pages)
    other = "https://example.com/folio/p/00000000-0000-0000-0000-000000000000-x"
    r = await _send(client, url, _shared("U_LUIS", guide, secret, other))
    assert r.json() == {"ok": True}
    await run_jobs(db)
    [call] = unfurls
    assert call["channel"] == "C1" and call["ts"] == "1.2"
    assert list(call["unfurls"]) == [guide]
    assert call["unfurls"][guide]["title"] == "Guía"
    assert call["unfurls"][guide]["text"] == METADATA["description"]
    await _send(client, url, _shared("U_X", guide))  # no Radicle account behind it
    await run_jobs(db)
    assert len(unfurls) == 1
    forged = await client.post(url, content=b"{}", headers={"X-Slack-Signature": "v0=0"})
    assert forged.status_code == 401
