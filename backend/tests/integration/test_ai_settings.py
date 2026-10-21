"""Admin, AI provider (Folio 0.3): saved encrypted, tested with a simulated provider,
audited without the key, and only for instance admins."""

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AiSettings, AuditEntry
from radicle.platform.services import ai
from tests.conftest import Team

API = "/api/v1"


@pytest.fixture
def fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Answers like OpenAI (/embeddings) or Ollama (/api/embed); a key 'bad' is rejected."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "bad" in request.headers.get("authorization", ""):
            return httpx.Response(401, json={"error": "invalid key"})
        if request.url.path.endswith("/api/embed"):
            return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [0.5] * 8}]})
        return httpx.Response(404, json={"error": "no such route"})

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    return seen


async def test_configure_encrypt_test_and_audit(
    client: AsyncClient, db: AsyncSession, board: Team, fake_embeddings: list[httpx.Request]
) -> None:
    i = board.instance.headers
    r = await client.get(f"{API}/admin/ai", headers=i)
    assert r.status_code == 200 and r.json()["provider"] == "none"
    r = await client.post(f"{API}/admin/ai/test", headers=i)
    assert r.json()["ok"] is False and "No AI provider" in r.json()["message"]

    r = await client.put(
        f"{API}/admin/ai",
        headers=i,
        json={
            "provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_dimensions": 8,
            "api_key": "sk-secret-123",
            "features": {"rag": True},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_key"] is True and "api_key" not in body
    assert body["base_url"] == "https://api.openai.com/v1"

    row = await db.get(AiSettings, 1)
    assert row is not None and row.api_key_encrypted
    assert "sk-secret-123" not in row.api_key_encrypted
    assert (await ai.load(db)).api_key == "sk-secret-123"

    r = await client.post(f"{API}/admin/ai/test", headers=i)
    out = r.json()
    assert out["ok"] is True and out["dimensions"] == 8 and out["latency_ms"] >= 0
    sent = fake_embeddings[-1]
    assert sent.headers["authorization"] == "Bearer sk-secret-123"
    assert b'"dimensions":8' in sent.content.replace(b" ", b"")

    entry = await db.scalar(
        select(AuditEntry).where(AuditEntry.target_id == "ai").order_by(AuditEntry.id.desc())
    )
    assert entry is not None and entry.app.value == "platform"
    assert "sk-secret-123" not in str(entry.details)
    assert entry.details["after"]["has_key"] is True


async def test_ollama_and_partial_changes(
    client: AsyncClient, board: Team, fake_embeddings: list[httpx.Request]
) -> None:
    i = board.instance.headers
    r = await client.put(
        f"{API}/admin/ai",
        headers=i,
        json={"provider": "ollama", "embedding_model": "nomic-embed-text"},
    )
    assert r.json()["base_url"] == "http://localhost:11434"
    r = await client.put(f"{API}/admin/ai", headers=i, json={"chat_model": "llama3.2"})
    assert r.json()["embedding_model"] == "nomic-embed-text"
    r = await client.post(f"{API}/admin/ai/test", headers=i)
    assert r.json()["ok"] is True and r.json()["dimensions"] == 3
    assert fake_embeddings[-1].url.path == "/api/embed"


async def test_actionable_errors(
    client: AsyncClient, board: Team, fake_embeddings: list[httpx.Request]
) -> None:
    i = board.instance.headers
    r = await client.put(f"{API}/admin/ai", headers=i, json={"provider": "nope"})
    assert r.status_code == 422
    r = await client.put(
        f"{API}/admin/ai", headers=i, json={"provider": "openai", "base_url": "ftp://x"}
    )
    assert r.status_code == 422 and "http://" in r.json()["detail"]
    r = await client.put(f"{API}/admin/ai", headers=i, json={"provider": "openai_compatible"})
    assert r.status_code == 422 and "base URL" in r.json()["detail"]
    r = await client.put(f"{API}/admin/ai", headers=i, json={"embedding_dimensions": 0})
    assert r.status_code == 422

    await client.put(f"{API}/admin/ai", headers=i, json={"provider": "anthropic"})
    r = await client.post(f"{API}/admin/ai/test", headers=i)
    assert r.json()["ok"] is False and "no embeddings API" in r.json()["message"]

    await client.put(
        f"{API}/admin/ai",
        headers=i,
        json={"provider": "openai", "embedding_model": "m", "api_key": "bad-key"},
    )
    r = await client.post(f"{API}/admin/ai/test", headers=i)
    assert r.json()["ok"] is False and "rejected the API key" in r.json()["message"]

    r = await client.put(f"{API}/admin/ai", headers=i, json={"api_key": ""})
    assert r.json()["has_key"] is False


@pytest.mark.parametrize("role", ["admin", "member", "agent"])
async def test_only_instance_admins(client: AsyncClient, board: Team, role: str) -> None:
    headers = board.by_role(role).headers
    assert (await client.get(f"{API}/admin/ai", headers=headers)).status_code == 403
    r = await client.put(f"{API}/admin/ai", headers=headers, json={"provider": "openai"})
    assert r.status_code == 403
    assert (await client.post(f"{API}/admin/ai/test", headers=headers)).status_code == 403
