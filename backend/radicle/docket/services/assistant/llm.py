"""Calls to the configured LLM: Anthropic's Messages API or any OpenAI-compatible server."""

import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from radicle.docket.services.assistant.config import DEFAULT_BASE_URL, AssistantConfig
from radicle.platform.errors import ProblemError

# Tests swap this for an httpx.MockTransport.
transport: httpx.AsyncBaseTransport | None = None
TIMEOUT = 45.0
MAX_TOKENS = 900
# OpenAI counts a reasoning model's thinking in this budget too, so it gets more room.
OPENAI_MAX_TOKENS = 4000
Tool = dict[str, Any] | None


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


class AssistantUnavailable(ProblemError):
    status = 502
    code = "assistant_unavailable"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, transport=transport)


@dataclass(frozen=True)
class Completion:
    text: str
    tool_input: dict[str, Any] | None = None  # arguments of the tool the model called


async def complete(cfg: AssistantConfig, system: str, messages: list[Message]) -> str:
    """The model's answer, or AssistantUnavailable with what to fix."""
    return (await converse(cfg, system, messages)).text


Api = Literal["anthropic", "responses", "chat"]


def _api(cfg: AssistantConfig) -> Api:
    if cfg.provider == "anthropic":
        return "anthropic"
    # OpenAI's newer models only take tools through the Responses API; compatible servers
    # (Ollama, vLLM) speak Chat Completions.
    return "responses" if cfg.base_url == DEFAULT_BASE_URL["openai"] else "chat"


def _request(
    api: Api, cfg: AssistantConfig, system: str, turns: list[dict[str, str]], tool: Tool
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """The URL, headers and body each API expects."""
    if api == "anthropic":
        body: dict[str, Any] = {
            "model": cfg.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": turns,
        }
        if tool:
            body["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["parameters"],
                }
            ]
        headers = {"x-api-key": cfg.api_key or "", "anthropic-version": "2023-06-01"}
        return f"{cfg.base_url}/v1/messages", headers, body
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    if api == "responses":
        body = {
            "model": cfg.model,
            "instructions": system,
            "input": turns,
            "max_output_tokens": OPENAI_MAX_TOKENS,
            "store": False,  # nothing kept on OpenAI's side
        }
        if tool:
            body["tools"] = [{"type": "function", **tool}]
        return f"{cfg.base_url}/responses", headers, body
    body = {
        "model": cfg.model,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system}, *turns],
    }
    if tool:
        body["tools"] = [{"type": "function", "function": tool}]
    return f"{cfg.base_url}/chat/completions", headers, body


async def converse(
    cfg: AssistantConfig,
    system: str,
    messages: list[Message],
    tool: Tool = None,
) -> Completion:
    """Like `complete`, offering the model one tool it may call alongside its text."""
    api = _api(cfg)
    turns = [{"role": m.role, "content": m.content} for m in messages]
    url, headers, body = _request(api, cfg, system, turns, tool)
    try:
        async with _client() as client:
            r = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise AssistantUnavailable(
            f"Could not reach {cfg.base_url} ({exc.__class__.__name__}). "
            "Check the base URL in Admin → Settings → Assistant."
        ) from exc
    if r.status_code in (401, 403):
        raise AssistantUnavailable(
            f"The {cfg.provider} API rejected the key. Paste a valid one in Admin → Settings."
        )
    if r.status_code >= 400:
        detail = r.text[:200].replace("\n", " ")
        raise AssistantUnavailable(f"The {cfg.provider} API answered {r.status_code}: {detail}")
    try:
        return _parse(api, r.json())
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AssistantUnavailable(
            f"Unexpected answer from {cfg.provider}; is '{cfg.model}' a chat model?"
        ) from exc


def _parse(api: Api, data: dict[str, Any]) -> Completion:
    if api == "anthropic":
        blocks = data["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        used = next((b for b in blocks if b.get("type") == "tool_use"), None)
        return Completion(text, used["input"] if used else None)
    if api == "responses":
        items = data["output"]
        text = "".join(
            part.get("text", "")
            for item in items
            if item.get("type") == "message"
            for part in item["content"]
            if part.get("type") == "output_text"
        ).strip()
        call = next((i for i in items if i.get("type") == "function_call"), None)
        return Completion(text, json.loads(call["arguments"]) if call else None)
    message = data["choices"][0]["message"]
    calls = message.get("tool_calls") or []
    tool_input = json.loads(calls[0]["function"]["arguments"]) if calls else None
    return Completion(str(message.get("content") or "").strip(), tool_input)
