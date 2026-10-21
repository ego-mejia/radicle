"""The instance's AI provider (Folio 0.3): one setting for chat and embeddings that every
app reads. The key is encrypted; without a provider everything else keeps working."""

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.db.models import AiCall, AiProvider, AiSettings, User, utcnow
from radicle.platform.errors import ProblemError, ValidationFailed

# Tests swap this for an httpx.MockTransport.
transport: httpx.AsyncBaseTransport | None = None
TIMEOUT = 30.0
MAX_DIMENSIONS = 8192
DEFAULT_BASE_URL: dict[AiProvider, str] = {
    AiProvider.anthropic: "https://api.anthropic.com",
    AiProvider.openai: "https://api.openai.com/v1",
    AiProvider.ollama: "http://localhost:11434",
}


class AiUnavailable(ProblemError):
    status = 502
    code = "ai_unavailable"


@dataclass(frozen=True)
class AiConfig:
    provider: AiProvider = AiProvider.none
    chat_model: str = ""
    embedding_model: str = ""
    embedding_dimensions: int | None = None
    base_url: str = ""
    api_key: str | None = None
    features: dict[str, bool] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return self.provider != AiProvider.none

    def view(self) -> dict[str, Any]:
        """What the admin screen and the audit log show: never the key itself."""
        return {
            "provider": self.provider.value,
            "chat_model": self.chat_model,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "base_url": self.base_url,
            "has_key": bool(self.api_key),
            "features": dict(self.features),
        }


def _config(row: AiSettings | None) -> AiConfig:
    if row is None:
        return AiConfig()
    return AiConfig(
        provider=row.provider,
        chat_model=row.chat_model or "",
        embedding_model=row.embedding_model or "",
        embedding_dimensions=row.embedding_dimensions,
        base_url=row.base_url or DEFAULT_BASE_URL.get(row.provider, ""),
        api_key=crypto.decrypt(row.api_key_encrypted) if row.api_key_encrypted else None,
        features={k: bool(v) for k, v in (row.features or {}).items()},
    )


async def load(db: AsyncSession) -> AiConfig:
    return _config(await db.get(AiSettings, 1))


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


def _provider(value: Any) -> AiProvider:
    try:
        return AiProvider(str(value).strip().lower())
    except ValueError:
        valid = ", ".join(p.value for p in AiProvider)
        raise _invalid("provider", f"Unknown AI provider '{value}'. Use one of: {valid}.") from None


async def save(db: AsyncSession, actor: User, changes: dict[str, Any]) -> AiConfig:
    """Apply the fields sent. `api_key`: a new key, '' to remove it, absent to keep it."""
    row = await db.get(AiSettings, 1)
    if row is None:
        row = AiSettings(id=1, provider=AiProvider.none, features={})
        db.add(row)
    if "provider" in changes:
        row.provider = _provider(changes["provider"])
    for name in ("chat_model", "embedding_model", "base_url"):
        if name in changes:
            setattr(row, name, (changes[name] or "").strip() or None)
    if row.base_url and not row.base_url.startswith(("http://", "https://")):
        raise _invalid("base_url", "The base URL must start with http:// or https://.")
    if row.base_url:
        row.base_url = row.base_url.rstrip("/")
    if row.provider == AiProvider.openai_compatible and not row.base_url:
        raise _invalid("base_url", "An OpenAI-compatible provider needs its base URL.")
    if "embedding_dimensions" in changes:
        dims = changes["embedding_dimensions"]
        if dims is not None and not (isinstance(dims, int) and 1 <= dims <= MAX_DIMENSIONS):
            raise _invalid(
                "embedding_dimensions", f"Embedding dimensions go from 1 to {MAX_DIMENSIONS}."
            )
        row.embedding_dimensions = dims
    if "features" in changes:
        row.features = {str(k): bool(v) for k, v in (changes["features"] or {}).items()}
    if "api_key" in changes:
        key = (changes["api_key"] or "").strip()
        row.api_key_encrypted = crypto.encrypt(key) if key else None
    row.updated_by = actor.id
    row.updated_at = utcnow()
    await db.flush()
    return _config(row)


@dataclass(frozen=True)
class Embedding:
    vector: list[float]
    latency_ms: int


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, transport=transport)


def _embedding_request(
    cfg: AiConfig, inputs: str | list[str]
) -> tuple[str, dict[str, str], dict[str, Any]]:
    if not cfg.enabled:
        raise AiUnavailable("No AI provider is configured. Choose one in Admin, AI provider.")
    if cfg.provider == AiProvider.anthropic:
        raise AiUnavailable(
            "Anthropic has no embeddings API. For embeddings use openai, an "
            "openai_compatible server (for example Voyage) or ollama.",
            code="no_embeddings",
        )
    if not cfg.embedding_model:
        raise AiUnavailable("Set an embedding model first, e.g. text-embedding-3-small.")
    if cfg.provider == AiProvider.ollama:
        return f"{cfg.base_url}/api/embed", {}, {"model": cfg.embedding_model, "input": inputs}
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    body: dict[str, Any] = {"model": cfg.embedding_model, "input": inputs}
    if cfg.embedding_dimensions:
        body["dimensions"] = cfg.embedding_dimensions
    return f"{cfg.base_url}/embeddings", headers, body


def _vectors(cfg: AiConfig, data: dict[str, Any], count: int) -> list[list[float]]:
    try:
        if cfg.provider == AiProvider.ollama:
            raw = data["embeddings"]
        else:
            raw = [d["embedding"] for d in sorted(data["data"], key=lambda d: d.get("index", 0))]
        vectors = [[float(x) for x in v] for v in raw]
    except (KeyError, IndexError, TypeError, ValueError):
        raise AiUnavailable("The provider answered, but not with an embedding.") from None
    if len(vectors) != count or not all(vectors):
        raise AiUnavailable("The provider answered, but not with an embedding.")
    return vectors


async def _post(cfg: AiConfig, inputs: str | list[str]) -> tuple[dict[str, Any], int]:
    url, headers, body = _embedding_request(cfg, inputs)
    started = time.perf_counter()
    try:
        async with _client() as client:
            r = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise AiUnavailable(f"Could not reach {cfg.base_url}: {exc.__class__.__name__}.") from exc
    latency = int((time.perf_counter() - started) * 1000)
    if r.status_code in (401, 403):
        raise AiUnavailable("The provider rejected the API key. Check it in Admin, AI provider.")
    if r.status_code >= 400:
        raise AiUnavailable(f"The provider answered {r.status_code}: {r.text[:200]}")
    return r.json(), latency


async def embed(cfg: AiConfig, text: str) -> Embedding:
    """One embedding, or AiUnavailable saying what to fix."""
    data, latency = await _post(cfg, text)
    return Embedding(vector=_vectors(cfg, data, 1)[0], latency_ms=latency)


async def embed_many(cfg: AiConfig, texts: list[str]) -> list[list[float]]:
    """One embedding per text, in order, in a single request."""
    if not texts:
        return []
    data, _ = await _post(cfg, texts)
    return _vectors(cfg, data, len(texts))


@dataclass(frozen=True)
class Turn:
    role: str  # "user" or "assistant"
    content: str


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


CHAT_MAX_TOKENS = 1500


def _chat_request(
    cfg: AiConfig, system: str, turns: list[Turn], max_tokens: int
) -> tuple[str, dict[str, str], dict[str, Any]]:
    if not cfg.enabled:
        raise AiUnavailable("No AI provider is configured. Choose one in Admin, AI provider.")
    if not cfg.chat_model:
        raise AiUnavailable("Set a chat model first in Admin, AI provider.")
    messages = [{"role": t.role, "content": t.content} for t in turns]
    if cfg.provider == AiProvider.anthropic:
        headers = {"x-api-key": cfg.api_key or "", "anthropic-version": "2023-06-01"}
        body = {
            "model": cfg.chat_model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        return f"{cfg.base_url}/v1/messages", headers, body
    full = [{"role": "system", "content": system}, *messages]
    if cfg.provider == AiProvider.ollama:
        body = {"model": cfg.chat_model, "messages": full, "stream": False}
        return f"{cfg.base_url}/api/chat", {}, body
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    body = {"model": cfg.chat_model, "messages": full, "max_completion_tokens": max_tokens}
    return f"{cfg.base_url}/chat/completions", headers, body


def _reply(cfg: AiConfig, data: dict[str, Any], latency: int) -> Reply:
    try:
        if cfg.provider == AiProvider.anthropic:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            usage = data.get("usage") or {}
            tokens = (usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        elif cfg.provider == AiProvider.ollama:
            text = data["message"]["content"]
            tokens = (data.get("prompt_eval_count", 0), data.get("eval_count", 0))
        else:
            text = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage") or {}
            tokens = (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
    except (KeyError, IndexError, TypeError):
        raise AiUnavailable(
            f"The provider answered, but not with a chat reply. Is '{cfg.chat_model}' a chat model?"
        ) from None
    return Reply(str(text).strip(), int(tokens[0] or 0), int(tokens[1] or 0), latency)


async def chat(
    db: AsyncSession,
    cfg: AiConfig,
    system: str,
    turns: list[Turn],
    *,
    app: str,
    feature: str,
    user: User | None,
    max_tokens: int = CHAT_MAX_TOKENS,
) -> Reply:
    """The model's answer; every call, failed or not, is recorded in ai_calls without
    its content."""
    url, headers, body = _chat_request(cfg, system, turns, max_tokens)
    call = AiCall(
        app=app,
        feature=feature,
        user_id=user.id if user else None,
        provider=cfg.provider.value,
        model=cfg.chat_model,
        ok=False,
    )
    db.add(call)
    started = time.perf_counter()
    try:
        try:
            async with _client() as client:
                r = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise AiUnavailable(
                f"Could not reach {cfg.base_url}: {exc.__class__.__name__}."
            ) from exc
        call.latency_ms = int((time.perf_counter() - started) * 1000)
        if r.status_code in (401, 403):
            raise AiUnavailable(
                "The provider rejected the API key. Check it in Admin, AI provider."
            )
        if r.status_code >= 400:
            raise AiUnavailable(f"The provider answered {r.status_code}: {r.text[:200]}")
        reply = _reply(cfg, r.json(), call.latency_ms)
    finally:
        call.latency_ms = call.latency_ms or int((time.perf_counter() - started) * 1000)
        await db.flush()
    call.ok = True
    call.input_tokens, call.output_tokens = reply.input_tokens, reply.output_tokens
    await db.flush()
    return reply


def _stream_body(cfg: AiConfig, body: dict[str, Any]) -> dict[str, Any]:
    body = {**body, "stream": True}
    if cfg.provider not in (AiProvider.anthropic, AiProvider.ollama):
        body["stream_options"] = {"include_usage": True}
    return body


def _piece(cfg: AiConfig, event: dict[str, Any], call: AiCall) -> str:
    """The text in one streamed event; usage events fill in the call's tokens."""
    if cfg.provider == AiProvider.anthropic:
        kind = event.get("type")
        if kind == "message_start":
            call.input_tokens = int(event["message"].get("usage", {}).get("input_tokens", 0))
        elif kind == "message_delta":
            call.output_tokens = int(event.get("usage", {}).get("output_tokens", 0))
        elif kind == "content_block_delta" and event["delta"].get("type") == "text_delta":
            return str(event["delta"]["text"])
        elif kind == "error":
            message = (event.get("error") or {}).get("message", "unknown error")
            raise AiUnavailable(f"The provider stopped answering: {message}")
        return ""
    if cfg.provider == AiProvider.ollama:
        if event.get("done"):
            call.input_tokens = int(event.get("prompt_eval_count", 0))
            call.output_tokens = int(event.get("eval_count", 0))
        return str((event.get("message") or {}).get("content") or "")
    if event.get("usage"):
        call.input_tokens = int(event["usage"].get("prompt_tokens", 0))
        call.output_tokens = int(event["usage"].get("completion_tokens", 0))
    choices = event.get("choices") or []
    return str((choices[0].get("delta") or {}).get("content") or "") if choices else ""


def _event(line: str) -> dict[str, Any] | None:
    """Server-sent events (`data: {...}`) or Ollama's one JSON object per line."""
    raw = line[5:].strip() if line.startswith("data:") else line.strip()
    if not raw or raw == "[DONE]" or not raw.startswith("{"):
        return None
    parsed: dict[str, Any] = json.loads(raw)
    return parsed


async def stream(
    db: AsyncSession,
    cfg: AiConfig,
    system: str,
    turns: list[Turn],
    *,
    app: str,
    feature: str,
    user: User | None,
    max_tokens: int = CHAT_MAX_TOKENS,
) -> AsyncIterator[str]:
    """Like `chat`, but the answer arrives piece by piece as the model writes it. The call
    is recorded in ai_calls when the stream ends, failed or not."""
    url, headers, body = _chat_request(cfg, system, turns, max_tokens)
    call = AiCall(
        app=app,
        feature=feature,
        user_id=user.id if user else None,
        provider=cfg.provider.value,
        model=cfg.chat_model,
        ok=False,
    )
    db.add(call)
    started = time.perf_counter()
    try:
        async with (
            _client() as client,
            client.stream("POST", url, headers=headers, json=_stream_body(cfg, body)) as r,
        ):
            if r.status_code in (401, 403):
                raise AiUnavailable(
                    "The provider rejected the API key. Check it in Admin, AI provider."
                )
            if r.status_code >= 400:
                detail = (await r.aread()).decode(errors="replace")[:200]
                raise AiUnavailable(f"The provider answered {r.status_code}: {detail}")
            async for line in r.aiter_lines():
                event = _event(line)
                piece = _piece(cfg, event, call) if event else ""
                if piece:
                    yield piece
        call.ok = True
    except httpx.HTTPError as exc:
        raise AiUnavailable(f"Could not reach {cfg.base_url}: {exc.__class__.__name__}.") from exc
    except (KeyError, TypeError, ValueError):
        raise AiUnavailable(
            f"The provider answered, but not with a chat reply. Is '{cfg.chat_model}' a chat model?"
        ) from None
    finally:
        call.latency_ms = int((time.perf_counter() - started) * 1000)
        await db.flush()
