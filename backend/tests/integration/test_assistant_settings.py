"""Admins pick Radi's LLM in the app (key encrypted) unless environment variables do."""

import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import InstanceSetting
from radicle.docket.services.assistant import llm
from radicle.platform.config import get_settings
from tests.conftest import Team

API = "/api/v1"


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Answers like Anthropic or OpenAI; a key 'bad' is rejected."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        auth = request.headers.get("x-api-key") or request.headers.get("authorization", "")
        if "bad" in auth:
            return httpx.Response(401, json={"error": "invalid key"})
        if request.url.path.endswith("/v1/messages"):
            return httpx.Response(200, json={"content": [{"type": "text", "text": "OK"}]})
        if request.url.path.endswith("/responses"):
            message = {"type": "message", "content": [{"type": "output_text", "text": "OK"}]}
            return httpx.Response(200, json={"output": [message]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(handler))
    return seen


async def test_configure_test_and_audit(
    client: AsyncClient, db: AsyncSession, board: Team, fake_llm: list[httpx.Request]
) -> None:
    i = board.instance.headers
    r = await client.get(f"{API}/admin/assistant", headers=i)
    assert r.json() == {
        "provider": "none",
        "model": "",
        "base_url": "",
        "has_key": False,
        "managed_by_env": False,
    }
    r = await client.post(f"{API}/admin/assistant/test", headers=i)
    assert r.json()["ok"] is False

    r = await client.put(
        f"{API}/admin/assistant",
        headers=i,
        json={"provider": "anthropic", "api_key": "sk-secret-123"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["has_key"] and r.json()["model"] == "claude-haiku-5-5"
    assert "sk-secret" not in r.text
    row = await db.scalar(select(InstanceSetting).where(InstanceSetting.key == "assistant"))
    assert row is not None and row.value["api_key"].startswith("v1:")
    assert "sk-secret" not in json.dumps(row.value)

    r = await client.post(f"{API}/admin/assistant/test", headers=i)
    assert r.json() == {"ok": True, "message": "claude-haiku-5-5 answered: OK"}
    assert fake_llm[-1].headers["x-api-key"] == "sk-secret-123"

    # An OpenAI-compatible local server without a key, then a bad key.
    r = await client.put(
        f"{API}/admin/assistant",
        headers=i,
        json={
            "provider": "openai",
            "base_url": "http://ollama:11434/v1",
            "model": "llama3",
            "api_key": "",
        },
    )
    assert r.json()["has_key"] is False
    assert (await client.post(f"{API}/admin/assistant/test", headers=i)).json()["ok"] is True
    assert str(fake_llm[-1].url) == "http://ollama:11434/v1/chat/completions"
    await client.put(f"{API}/admin/assistant", headers=i, json={"api_key": "bad"})
    r = await client.post(f"{API}/admin/assistant/test", headers=i)
    assert r.json()["ok"] is False and "rejected the key" in r.json()["message"]

    entries = (await client.get(f"{API}/audit", headers=i, params={"action": "settings"})).json()[
        "items"
    ]
    changes = [e for e in entries if e["target_id"] == "assistant"]
    assert changes and "sk-secret" not in json.dumps(changes)


async def test_validation_env_and_permissions(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    i = board.instance.headers
    r = await client.put(f"{API}/admin/assistant", headers=i, json={"provider": "gemini"})
    assert r.status_code == 422
    r = await client.put(f"{API}/admin/assistant", headers=i, json={"base_url": "ftp://x"})
    assert r.status_code == 422
    r = await client.get(f"{API}/admin/assistant", headers=board.admin.headers)
    assert r.status_code == 403

    monkeypatch.setattr(get_settings(), "assistant_provider", "anthropic")
    monkeypatch.setattr(get_settings(), "assistant_api_key", "from-env")
    r = await client.get(f"{API}/admin/assistant", headers=i)
    assert r.json()["managed_by_env"] is True and r.json()["has_key"] is True
    r = await client.put(f"{API}/admin/assistant", headers=i, json={"provider": "none"})
    assert r.status_code == 409 and "environment variables" in r.json()["detail"]
