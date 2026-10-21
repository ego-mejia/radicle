"""Streamed chat (Folio 4.5): each provider's stream format, usage in ai_calls when the
stream ends, and actionable errors."""

import json

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AiCall, AiProvider
from radicle.platform.services import ai

TURNS = [ai.Turn("user", "¿Cómo conecto un agente?")]


def sse(*events: dict) -> bytes:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()


ANTHROPIC = sse(
    {"type": "message_start", "message": {"usage": {"input_tokens": 120}}},
    {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Ve a "}},
    {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Admin [1]."}},
    {"type": "message_delta", "usage": {"output_tokens": 7}},
)
OPENAI = (
    sse(
        {"choices": [{"delta": {"content": "Ve a "}}]},
        {"choices": [{"delta": {"content": "Admin [1]."}}]},
        {"choices": [], "usage": {"prompt_tokens": 120, "completion_tokens": 7}},
    )
    + b"data: [DONE]\n\n"
)
OLLAMA = (
    json.dumps({"message": {"content": "Ve a "}, "done": False})
    + "\n"
    + json.dumps({"message": {"content": "Admin [1]."}, "done": False})
    + "\n"
    + json.dumps({"done": True, "prompt_eval_count": 120, "eval_count": 7})
    + "\n"
).encode()


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "bad" in request.headers.get("x-api-key", ""):
            return httpx.Response(401, json={"error": "invalid key"})
        path = request.url.path
        body = {"/v1/messages": ANTHROPIC, "/api/chat": OLLAMA}.get(path, OPENAI)
        return httpx.Response(200, content=body)

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    return requests


def _cfg(provider: AiProvider, **kw: object) -> ai.AiConfig:
    base = {"provider": provider, "chat_model": "m", "api_key": "k"}
    base["base_url"] = ai.DEFAULT_BASE_URL.get(provider, "http://llm.local/v1")
    return ai.AiConfig(**{**base, **kw})  # type: ignore[arg-type]


async def _collect(db: AsyncSession, cfg: ai.AiConfig) -> list[str]:
    stream = ai.stream(db, cfg, "s", TURNS, app="folio", feature="chat", user=None)
    return [piece async for piece in stream]


@pytest.mark.parametrize(
    "provider", [AiProvider.anthropic, AiProvider.openai, AiProvider.ollama], ids=str
)
async def test_each_provider_streams_and_counts_usage(
    db: AsyncSession, sent: list[httpx.Request], provider: AiProvider
) -> None:
    assert await _collect(db, _cfg(provider)) == ["Ve a ", "Admin [1]."]
    body = json.loads(sent[0].content)
    assert body["stream"] is True
    if provider == AiProvider.openai:
        assert body["stream_options"] == {"include_usage": True}
    call = await db.scalar(select(AiCall))
    assert call is not None and call.ok and call.feature == "chat"
    assert (call.input_tokens, call.output_tokens) == (120, 7)


async def test_errors_are_recorded_and_say_what_to_fix(
    db: AsyncSession, sent: list[httpx.Request]
) -> None:
    with pytest.raises(ai.AiUnavailable, match="API key"):
        await _collect(db, _cfg(AiProvider.anthropic, api_key="bad"))
    with pytest.raises(ai.AiUnavailable, match="No AI provider"):
        await _collect(db, ai.AiConfig())
    calls = list(await db.scalars(select(AiCall)))
    assert [c.ok for c in calls] == [False]
