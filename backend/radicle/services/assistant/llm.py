"""Calls to the configured LLM: Anthropic's Messages API or any OpenAI-compatible server."""

import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from radicle.core.errors import ProblemError
from radicle.services.assistant.config import AssistantConfig

# Tests swap this for an httpx.MockTransport.
transport: httpx.AsyncBaseTransport | None = None
TIMEOUT = 45.0
MAX_TOKENS = 900


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


async def converse(
    cfg: AssistantConfig,
    system: str,
    messages: list[Message],
    tool: dict[str, Any] | None = None,
) -> Completion:
    """Like `complete`, offering the model one tool it may call alongside its text."""
    turns = [{"role": m.role, "content": m.content} for m in messages]
    try:
        async with _client() as client:
            if cfg.provider == "anthropic":
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
                r = await client.post(
                    f"{cfg.base_url}/v1/messages",
                    headers={"x-api-key": cfg.api_key or "", "anthropic-version": "2023-06-01"},
                    json=body,
                )
            else:
                body = {
                    "model": cfg.model,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "system", "content": system}, *turns],
                }
                if tool:
                    body["tools"] = [{"type": "function", "function": tool}]
                headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
                r = await client.post(
                    f"{cfg.base_url}/chat/completions", headers=headers, json=body
                )
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
        return _parse(cfg.provider, r.json())
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AssistantUnavailable(
            f"Unexpected answer from {cfg.provider}; is '{cfg.model}' a chat model?"
        ) from exc


def _parse(provider: str, data: dict[str, Any]) -> Completion:
    if provider == "anthropic":
        blocks = data["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        used = next((b for b in blocks if b.get("type") == "tool_use"), None)
        return Completion(text, used["input"] if used else None)
    message = data["choices"][0]["message"]
    calls = message.get("tool_calls") or []
    tool_input = json.loads(calls[0]["function"]["arguments"]) if calls else None
    return Completion(str(message.get("content") or "").strip(), tool_input)
