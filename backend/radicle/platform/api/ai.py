"""Admin, AI provider: the chat and embeddings provider every app shares (Folio 0.3)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.platform.api.deps import Db, InstanceAdmin
from radicle.platform.api.schemas import Input, Output
from radicle.platform.services import ai, audit

router = APIRouter(tags=["ai"])

Provider = Literal["none", "anthropic", "openai", "openai_compatible", "ollama"]


class AiSettingsOut(Output):
    provider: Provider
    chat_model: str
    embedding_model: str
    embedding_dimensions: int | None
    base_url: str
    has_key: bool = Field(description="The key itself is never returned")
    features: dict[str, bool]


class AiSettingsIn(Input):
    provider: Provider | None = None
    chat_model: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(default=None, description="null uses the model's")
    base_url: str | None = Field(default=None, description="Empty uses the provider's default")
    api_key: str | None = Field(default=None, description="'' removes it; omit to keep it")
    features: dict[str, bool] | None = Field(
        default=None, description="Which AI features are on, by name"
    )


class AiTestOut(Output):
    ok: bool
    message: str
    dimensions: int | None = None
    latency_ms: int | None = None


@router.get("/admin/ai", response_model=AiSettingsOut)
async def get_ai(_: InstanceAdmin, db: Db) -> AiSettingsOut:
    return AiSettingsOut(**(await ai.load(db)).view())


@router.put("/admin/ai", response_model=AiSettingsOut)
async def put_ai(body: AiSettingsIn, admin: InstanceAdmin, db: Db) -> AiSettingsOut:
    """Only the fields sent change. Without a provider, the rest of Radicle still works."""
    before = (await ai.load(db)).view()
    after = (await ai.save(db, admin, body.model_dump(exclude_unset=True))).view()
    audit.record(
        db,
        admin,
        "settings.change",
        target_type="instance",
        target_id="ai",
        before=before,
        after=after,
    )
    return AiSettingsOut(**after)


@router.post("/admin/ai/test", response_model=AiTestOut)
async def test_ai(_: InstanceAdmin, db: Db) -> AiTestOut:
    """Embed a short text with the configured model and report dimensions and latency."""
    cfg = await ai.load(db)
    try:
        result = await ai.embed(cfg, "Radicle connection test")
    except ai.AiUnavailable as exc:
        return AiTestOut(ok=False, message=exc.detail)
    dims = len(result.vector)
    return AiTestOut(
        ok=True,
        message=f"{cfg.embedding_model} answered with {dims} dimensions in {result.latency_ms} ms.",
        dimensions=dims,
        latency_ms=result.latency_ms,
    )
