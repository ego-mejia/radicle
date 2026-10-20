from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.api.deps import CurrentPrincipal, Db, InstanceAdmin
from radicle.api.ratelimit import SlidingWindowLimiter
from radicle.api.schemas.common import Input, Output
from radicle.core.errors import ValidationFailed
from radicle.services import audit
from radicle.services.assistant import chat, config, llm

router = APIRouter(tags=["assistant"])
chat_limiter = SlidingWindowLimiter()
CHATS_PER_MINUTE = 20


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


class ChatMessage(Input):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatIn(Input):
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)
    language: Literal["en", "es"] = "en"


class TourStepOut(Output):
    target: str = Field(description="data-tour id of the element in the web app")
    action: Literal["point", "click"]
    page: str | None = Field(description="Route it lives on; {project} is the current one")
    text: str


class ChatOut(Output):
    answer: str = Field(description="Markdown")
    mode: Literal["llm", "guide"] = Field(description="Who wrote it: the LLM or the guide")
    sources: list[str] = Field(description="Guide sections it is based on")
    notice: str | None = Field(default=None, description="Why the LLM was not used")
    tour: list[TourStepOut] = Field(default_factory=list, description="On-screen walkthrough")
    autoplay: bool = Field(default=False, description="Start the tour right away")


@router.post("/assistant/chat", response_model=ChatOut)
async def assistant_chat(body: ChatIn, principal: CurrentPrincipal, db: Db) -> ChatOut:
    """Ask Radi how to use Radicle. Answers come from the usage guide, written by the
    configured LLM when there is one."""
    if body.messages[-1].role != "user":
        raise ValidationFailed(
            "The last message must be the user's question.",
            errors=[{"field": "messages", "message": "last must be user"}],
        )
    chat_limiter.hit(f"assistant:{principal.user.id}", CHATS_PER_MINUTE)
    reply = await chat.answer(
        db,
        [llm.Message(m.role, m.content) for m in body.messages],
        body.language,
        admin=principal.user.is_instance_admin,
    )
    return ChatOut(
        answer=reply.answer,
        mode=reply.mode,
        sources=reply.sources,
        notice=reply.notice,
        tour=[TourStepOut(**step.view()) for step in reply.tour],
        autoplay=reply.autoplay,
    )
