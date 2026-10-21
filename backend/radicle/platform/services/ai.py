"""The instance's AI provider (Folio 0.3): one setting for chat and embeddings that every
app reads. The key is encrypted; without a provider everything else keeps working."""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.db.models import AiProvider, AiSettings, User, utcnow
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


def _embedding_request(cfg: AiConfig, text: str) -> tuple[str, dict[str, str], dict[str, Any]]:
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
        return f"{cfg.base_url}/api/embed", {}, {"model": cfg.embedding_model, "input": text}
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    body: dict[str, Any] = {"model": cfg.embedding_model, "input": text}
    if cfg.embedding_dimensions:
        body["dimensions"] = cfg.embedding_dimensions
    return f"{cfg.base_url}/embeddings", headers, body


def _vector(cfg: AiConfig, data: dict[str, Any]) -> list[float]:
    try:
        if cfg.provider == AiProvider.ollama:
            return [float(x) for x in data["embeddings"][0]]
        return [float(x) for x in data["data"][0]["embedding"]]
    except (KeyError, IndexError, TypeError, ValueError):
        raise AiUnavailable("The provider answered, but not with an embedding.") from None


async def embed(cfg: AiConfig, text: str) -> Embedding:
    """One embedding, or AiUnavailable saying what to fix."""
    url, headers, body = _embedding_request(cfg, text)
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
    return Embedding(vector=_vector(cfg, r.json()), latency_ms=latency)
