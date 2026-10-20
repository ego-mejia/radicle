from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.api.deps import Db, InstanceAdmin
from radicle.api.schemas.common import Input, Output
from radicle.services import audit
from radicle.services.assistant import config, llm

router = APIRouter(tags=["assistant"])


class AssistantSettingsOut(Output):
    provider: str = Field(description="anthropic, openai (any compatible server) or none")
    model: str
    base_url: str
    has_key: bool = Field(description="The key is stored encrypted and never shown")
    managed_by_env: bool = Field(description="RADICLE_ASSISTANT_* variables set it; read-only")


class AssistantSettingsIn(Input):
    provider: Literal["none", "anthropic", "openai"] | None = None
    model: str | None = None
    base_url: str | None = Field(default=None, description="Empty for the provider's default")
    api_key: str | None = Field(default=None, description="Write only; empty string removes it")


class AssistantTestOut(Output):
    ok: bool
    message: str


@router.get("/admin/assistant", response_model=AssistantSettingsOut)
async def get_assistant(_: InstanceAdmin, db: Db) -> AssistantSettingsOut:
    return AssistantSettingsOut(**(await config.load(db)).view())


@router.put("/admin/assistant", response_model=AssistantSettingsOut)
async def put_assistant(
    body: AssistantSettingsIn, admin: InstanceAdmin, db: Db
) -> AssistantSettingsOut:
    """Which LLM Radi uses. Without one, Radi answers from the usage guide."""
    before = (await config.load(db)).view()
    after = (await config.save(db, body.model_dump(exclude_unset=True))).view()
    audit.record(
        db,
        admin,
        "settings.change",
        target_type="instance",
        target_id="assistant",
        before=before,
        after=after,
    )
    return AssistantSettingsOut(**after)


@router.post("/admin/assistant/test", response_model=AssistantTestOut)
async def test_assistant(_: InstanceAdmin, db: Db) -> AssistantTestOut:
    """Send a tiny message to the configured model."""
    cfg = await config.load(db)
    if not cfg.enabled:
        return AssistantTestOut(ok=False, message="No provider configured: Radi uses the guide.")
    try:
        answer = await llm.complete(cfg, "Answer with one word.", [llm.Message("user", "Say OK.")])
    except llm.AssistantUnavailable as exc:
        return AssistantTestOut(ok=False, message=exc.detail)
    return AssistantTestOut(ok=True, message=f"{cfg.model} answered: {answer[:60]}")
