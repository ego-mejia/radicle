"""Platform chat calls (Folio 4): each provider's API, actionable errors, and usage in
ai_calls without the prompt or the answer."""

import json

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AiCall, AiProvider
from radicle.platform.services import ai

TURNS = [ai.Turn("user", "Resume esta página secreta")]


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "bad" in request.headers.get("x-api-key", "") + request.headers.get("authorization", ""):
            return httpx.Response(401, json={"error": "invalid key"})
        path = request.url.path
        if request.url.host == "odd.local":
            return httpx.Response(200, json={"unexpected": True})
        if path.endswith("/v1/messages"):
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": " Un resumen. "}],
                    "usage": {"input_tokens": 12, "output_tokens": 3},
                },
            )
        if path.endswith("/api/chat"):
            return httpx.Response(
                200,
                json={"message": {"content": "Hola"}, "prompt_eval_count": 5, "eval_count": 1},
            )
        if path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Listo"}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 2},
                },
            )
        return httpx.Response(404)

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    return requests


def _cfg(provider: AiProvider, **kw: object) -> ai.AiConfig:
    base = {"provider": provider, "chat_model": "m", "api_key": "k"}
    base["base_url"] = ai.DEFAULT_BASE_URL.get(provider, "http://llm.local/v1")
    return ai.AiConfig(**{**base, **kw})  # type: ignore[arg-type]


async def test_anthropic_answers_and_usage_is_recorded_without_content(
    db: AsyncSession, seen: list[httpx.Request]
) -> None:
    cfg = _cfg(AiProvider.anthropic, chat_model="claude-sonnet-5-5")
    reply = await ai.chat(db, cfg, "Eres útil.", TURNS, app="folio", feature="summarize", user=None)
    assert reply.text == "Un resumen." and (reply.input_tokens, reply.output_tokens) == (12, 3)
    body = json.loads(seen[0].content)
    assert body["system"] == "Eres útil." and body["model"] == "claude-sonnet-5-5"
    call = (await db.scalars(select(AiCall))).one()
    assert (call.app, call.feature, call.ok, call.input_tokens) == ("folio", "summarize", True, 12)
    assert "secreta" not in json.dumps(
        {c.name: str(getattr(call, c.name)) for c in AiCall.__table__.c}
    )


@pytest.mark.parametrize(
    ("provider", "text"), [(AiProvider.openai, "Listo"), (AiProvider.ollama, "Hola")]
)
async def test_openai_and_ollama(
    db: AsyncSession, seen: list[httpx.Request], provider: AiProvider, text: str
) -> None:
    reply = await ai.chat(db, _cfg(provider), "s", TURNS, app="folio", feature="x", user=None)
    assert reply.text == text
    assert json.loads(seen[0].content)["messages"][0] == {"role": "system", "content": "s"}


async def test_actionable_errors(db: AsyncSession, seen: list[httpx.Request]) -> None:
    with pytest.raises(ai.AiUnavailable, match="No AI provider"):
        await ai.chat(db, ai.AiConfig(), "s", TURNS, app="folio", feature="x", user=None)
    with pytest.raises(ai.AiUnavailable, match="chat model"):
        cfg = _cfg(AiProvider.openai, chat_model="")
        await ai.chat(db, cfg, "s", TURNS, app="folio", feature="x", user=None)
    with pytest.raises(ai.AiUnavailable, match="rejected the API key"):
        cfg = _cfg(AiProvider.anthropic, api_key="bad")
        await ai.chat(db, cfg, "s", TURNS, app="folio", feature="x", user=None)
    with pytest.raises(ai.AiUnavailable, match="not with a chat reply"):
        cfg = _cfg(AiProvider.openai_compatible, base_url="http://odd.local/v1")
        await ai.chat(db, cfg, "s", TURNS, app="folio", feature="x", user=None)
    seen.clear()
