"""Seeded docs and a simulated chat provider for the docs chat tests (Folio 4.5)."""

import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AiProvider, AiSettings, User
from radicle.platform.services import ai
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, METADATA

GUIDE = (
    "Todo sobre agentes en Radicle.\n\n# Antes de empezar\n\nNecesitas ser admin.\n\n"
    "# Conecta un agente\n\nCrea un agente en Admin, Agentes y conéctalo por MCP con su token.\n"
)
DEPLOY = "# Despliegue\n\nCómo subir Radicle a producción con Docker Compose.\n"


async def page(client: AsyncClient, team: Team, title: str, md: str, **meta: object) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
    )
    nid = r.json()["id"]
    await client.put(
        f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": md, "metadata": METADATA | meta}
    )
    assert (await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})).status_code == 201
    return nid


@pytest.fixture
async def docs(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    guide = await page(client, team, "Conecta un agente a Radicle", GUIDE)
    deploy = await page(
        client, team, "Guía de deploy", DEPLOY, owner=f"@{team.member.handle}", doc_type="guide"
    )
    await run_jobs(db)
    return {"guide": guide, "deploy": deploy}


def sse(*events: dict) -> bytes:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch, db: AsyncSession) -> list[dict]:
    """A provider that answers from passage [1] in two pieces; keeps what it was sent."""
    db.add(
        AiSettings(
            id=1,
            provider=AiProvider.anthropic,
            chat_model="claude-sonnet-5-5",
            base_url="https://api.anthropic.com",
            features={},
        )
    )
    sent: list[dict] = []

    def reply(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            content=sse(
                {"type": "message_start", "message": {"usage": {"input_tokens": 300}}},
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Ve a "}},
                {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Admin, Agentes [1]."},
                },
                {"type": "message_delta", "usage": {"output_tokens": 9}},
            ),
        )

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(reply))
    return sent


async def user(db: AsyncSession, handle: str) -> User:
    found = await db.scalar(select(User).where(User.handle == handle))
    assert found is not None
    return found
