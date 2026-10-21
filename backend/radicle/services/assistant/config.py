"""Which LLM Radi uses. Set in Admin → Settings (key encrypted) or by environment variables,
which win when present. Without a provider Radi still answers from the usage guide."""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.config import get_settings
from radicle.platform.errors import Conflict, ValidationFailed
from radicle.platform.services.sso import get_setting, set_setting

Provider = Literal["none", "anthropic", "openai"]
PROVIDERS: tuple[Provider, ...] = ("none", "anthropic", "openai")
KEY = "assistant"
DEFAULT_MODEL: dict[str, str] = {"anthropic": "claude-haiku-5-5", "openai": "gpt-4o-mini"}
DEFAULT_BASE_URL: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
}


@dataclass(frozen=True)
class AssistantConfig:
    provider: Provider
    model: str
    base_url: str
    api_key: str | None
    from_env: bool

    @property
    def enabled(self) -> bool:
        # Local OpenAI-compatible servers (Ollama) often need no key.
        return self.provider != "none" and (bool(self.api_key) or self.provider == "openai")

    def view(self) -> dict[str, Any]:
        """What the admin screen shows: never the key itself."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "has_key": bool(self.api_key),
            "managed_by_env": self.from_env,
        }


def _provider(value: str | None) -> Provider:
    value = (value or "none").strip().lower()
    if value not in PROVIDERS:
        raise ValidationFailed(
            f"Unknown assistant provider '{value}'. Use anthropic, openai or none.",
            errors=[{"field": "provider", "message": "invalid"}],
        )
    return value


def _build(
    provider: Provider, model: str | None, base_url: str | None, key: str | None, env: bool
) -> AssistantConfig:
    return AssistantConfig(
        provider=provider,
        model=(model or DEFAULT_MODEL.get(provider, "")).strip(),
        base_url=(base_url or DEFAULT_BASE_URL.get(provider, "")).strip().rstrip("/"),
        api_key=key or None,
        from_env=env,
    )


async def load(db: AsyncSession) -> AssistantConfig:
    s = get_settings()
    if s.assistant_provider:
        return _build(
            _provider(s.assistant_provider),
            s.assistant_model,
            s.assistant_base_url,
            s.assistant_api_key,
            True,
        )
    raw = await get_setting(db, KEY, {}) or {}
    key = raw.get("api_key")
    return _build(
        _provider(raw.get("provider")),
        raw.get("model"),
        raw.get("base_url"),
        crypto.decrypt(key) if key else None,
        False,
    )


async def save(db: AsyncSession, changes: dict[str, Any]) -> AssistantConfig:
    """Apply the fields sent. `api_key`: a new key, '' to remove it, absent to keep it."""
    if get_settings().assistant_provider:
        raise Conflict(
            "The assistant is configured by RADICLE_ASSISTANT_* environment variables. "
            "Change them on the server, or unset them to manage it here.",
            code="assistant_managed_by_env",
        )
    raw = dict(await get_setting(db, KEY, {}) or {})
    if "provider" in changes:
        raw["provider"] = _provider(changes["provider"])
    for field in ("model", "base_url"):
        if field in changes:
            raw[field] = (changes[field] or "").strip() or None
    if "api_key" in changes:
        key = (changes["api_key"] or "").strip()
        raw["api_key"] = crypto.encrypt(key) if key else None
    base = raw.get("base_url")
    if base and not base.startswith(("http://", "https://")):
        raise ValidationFailed(
            "The base URL must start with http:// or https://.",
            errors=[{"field": "base_url", "message": "invalid"}],
        )
    await set_setting(db, KEY, raw)
    return await load(db)
