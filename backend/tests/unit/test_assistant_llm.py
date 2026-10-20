"""OpenAI gets the Responses API; compatible servers keep Chat Completions."""

import json

import httpx
import pytest

from radicle.services.assistant import llm, tours
from radicle.services.assistant.config import AssistantConfig

STEPS = {"steps": [{"target": "nav.projects", "action": "click", "text": "Go"}]}


def config(base_url: str) -> AssistantConfig:
    return AssistantConfig("openai", "gpt-6.1-sol", base_url, "k", from_env=False)


async def ask(base_url: str, answer: dict, monkeypatch: pytest.MonkeyPatch) -> tuple:
    sent: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=answer)

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(reply))
    done = await llm.converse(
        config(base_url), "system", [llm.Message("user", "hi")], tours.SHOW_ME
    )
    return done, sent[0].url.path, json.loads(sent[0].content)


async def test_openai_uses_the_responses_api(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": "Sure."}]},
            {"type": "function_call", "name": "show_me", "arguments": json.dumps(STEPS)},
        ]
    }
    done, path, body = await ask("https://api.openai.com/v1", answer, monkeypatch)
    assert done == llm.Completion("Sure.", STEPS)
    assert path == "/v1/responses" and body["instructions"] == "system"
    assert body["tools"][0]["name"] == "show_me" and body["store"] is False
    assert "max_output_tokens" in body and "max_tokens" not in body


async def test_compatible_servers_keep_chat_completions(monkeypatch: pytest.MonkeyPatch) -> None:
    call = {"function": {"name": "show_me", "arguments": json.dumps(STEPS)}}
    answer = {"choices": [{"message": {"content": None, "tool_calls": [call]}}]}
    done, path, body = await ask("http://localhost:11434/v1", answer, monkeypatch)
    assert done == llm.Completion("", STEPS)
    assert path == "/v1/chat/completions" and body["messages"][0]["role"] == "system"
    assert body["tools"][0]["function"]["name"] == "show_me" and "max_tokens" in body
