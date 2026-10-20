"""Calls to the configured LLM: Anthropic's Messages API or any OpenAI-compatible server."""

from dataclasses import dataclass
from typing import Literal

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


async def complete(cfg: AssistantConfig, system: str, messages: list[Message]) -> str:
    """The model's answer, or AssistantUnavailable with what to fix."""
    try:
        async with _client() as client:
            if cfg.provider == "anthropic":
                r = await client.post(
                    f"{cfg.base_url}/v1/messages",
                    headers={
                        "x-api-key": cfg.api_key or "",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": cfg.model,
                        "max_tokens": MAX_TOKENS,
                        "system": system,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                    },
                )
            else:
                headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
                r = await client.post(
                    f"{cfg.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": cfg.model,
                        "max_tokens": MAX_TOKENS,
                        "messages": [
                            {"role": "system", "content": system},
                            *({"role": m.role, "content": m.content} for m in messages),
                        ],
                    },
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
    data = r.json()
    try:
        if cfg.provider == "anthropic":
            return "".join(b.get("text", "") for b in data["content"]).strip()
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AssistantUnavailable(
            f"Unexpected answer from {cfg.provider}; is '{cfg.model}' a chat model?"
        ) from exc
