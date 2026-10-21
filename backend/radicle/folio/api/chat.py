"""The docs chat over REST (Folio 4.5): sessions, a question answered by server-sent
events, feedback, and the admin's list of questions the docs didn't answer."""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal

import anyio
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import Field

from radicle.folio.db.chat import ChatFeedback, FolioChatMessage, FolioChatSession
from radicle.folio.services import chat as chat_service
from radicle.folio.services import search
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page

router = APIRouter(tags=["folio"])


class ChatAvailabilityOut(Output):
    available: bool
    message: str | None = Field(description="Why it is off and who can turn it on")


class ChatSessionIn(Input):
    title: str = Field(default="", max_length=80)


class ChatSessionOut(Output):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class CitationOut(Output):
    n: int = Field(description="The [n] the answer uses")
    node_id: uuid.UUID
    version: int | None
    anchor: str | None = Field(description="The section's anchor; None for the page's start")
    title: str
    section: str
    url: str = Field(description="Link to the page at the section")
    outdated: bool = Field(description="The doc is marked Outdated: show a warning")


class ChatMessageOut(Output):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[CitationOut]
    feedback: Literal["up", "down"] | None
    created_at: datetime


class ChatSessionDetailOut(ChatSessionOut):
    messages: list[ChatMessageOut]


class ChatQuestionIn(Input):
    content: str = Field(min_length=1, max_length=chat_service.MAX_QUESTION)
    space: str | None = Field(default=None, description="Only docs in this space")
    doc_type: str | None = Field(default=None, description="Only docs of this type")
    audience: str | None = Field(default=None, description="Only docs for this audience")


class ChatFeedbackIn(Input):
    value: Literal["up", "down"]
    note: str | None = Field(default=None, max_length=1000)


class UnansweredOut(Output):
    question: str
    answer: str
    feedback: Literal["up", "down"] | None
    feedback_note: str | None
    asked_at: datetime


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


def _session(s: FolioChatSession) -> ChatSessionOut:
    return ChatSessionOut(id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at)


def _message(m: FolioChatMessage) -> ChatMessageOut:
    return ChatMessageOut.model_validate(chat_service.message_view(m))


@router.get("/chat/availability", response_model=ChatAvailabilityOut)
async def chat_availability(principal: CurrentPrincipal, db: Db) -> ChatAvailabilityOut:
    """Whether the chat shows at all: it needs an AI provider with a chat model."""
    await _reader(db, principal)
    off = await chat_service.unavailable(db)
    return ChatAvailabilityOut(available=off is None, message=off)


@router.get("/chat/sessions", response_model=Page[ChatSessionOut])
async def list_chat_sessions(
    principal: CurrentPrincipal, db: Db, limit: int = Query(default=30, ge=1, le=100)
) -> Page[ChatSessionOut]:
    """Your chat sessions, the most recent first."""
    await _reader(db, principal)
    sessions = await chat_service.list_sessions(db, principal.user, limit)
    return Page[ChatSessionOut](items=[_session(s) for s in sessions])


@router.post("/chat/sessions", response_model=ChatSessionOut, status_code=201)
async def create_chat_session(
    body: ChatSessionIn, principal: CurrentPrincipal, db: Db
) -> ChatSessionOut:
    """A new, empty session; its title comes from the first question if you leave it out."""
    await _reader(db, principal)
    return _session(await chat_service.create_session(db, principal.user, body.title))


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionDetailOut)
async def get_chat_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> ChatSessionDetailOut:
    """A session of yours with its questions and answers."""
    await _reader(db, principal)
    session = await chat_service.get_session(db, principal.user, session_id)
    found = await chat_service.messages(db, session)
    return ChatSessionDetailOut(
        **_session(session).model_dump(), messages=[_message(m) for m in found]
    )


@router.post(
    "/chat/sessions/{session_id}/messages",
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def ask_in_chat_session(
    session_id: uuid.UUID, body: ChatQuestionIn, principal: CurrentPrincipal, db: Db
) -> StreamingResponse:
    """Ask the docs. The answer streams as server-sent events: `delta` with `{text}` as it is
    written, then `done` with the saved message and its citations, or `error`."""
    await _reader(db, principal)
    session = await chat_service.get_session(db, principal.user, session_id)
    filters = search.Filters(space=body.space, doc_type=body.doc_type, audience=body.audience)
    events = await chat_service.ask(db, principal.user, session, body.content, filters=filters)

    async def body_stream() -> AsyncIterator[str]:
        # The request's session already committed before the stream started: the answer
        # and its ai_calls row are only kept if the stream commits them. `done` commits
        # before it is sent, so a reader who leaves right after still has the answer.
        try:
            async for event in events:
                if event.name == "done":
                    with anyio.CancelScope(shield=True):
                        await db.commit()
                yield f"event: {event.name}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
        finally:
            with anyio.CancelScope(shield=True):
                await db.commit()

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(body_stream(), media_type="text/event-stream", headers=headers)


@router.post("/chat/messages/{message_id}/feedback", response_model=ChatMessageOut)
async def give_chat_feedback(
    message_id: uuid.UUID, body: ChatFeedbackIn, principal: CurrentPrincipal, db: Db
) -> ChatMessageOut:
    """Thumbs up or down on one of your answers, with an optional note."""
    await _reader(db, principal)
    message = await chat_service.give_feedback(
        db, principal.user, message_id, ChatFeedback(body.value), body.note
    )
    return _message(message)


@router.get("/admin/chat/unanswered", response_model=Page[UnansweredOut])
async def unanswered_questions(
    principal: CurrentPrincipal, db: Db, limit: int = Query(default=50, ge=1, le=200)
) -> Page[UnansweredOut]:
    """Folio admins: questions the docs didn't answer, or whose answer got a thumbs down."""
    rows = await chat_service.unanswered(db, principal.user, limit)
    return Page[UnansweredOut](
        items=[
            UnansweredOut(
                question=r.question,
                answer=r.answer,
                feedback=r.feedback,
                feedback_note=r.feedback_note,
                asked_at=r.asked_at,
            )
            for r in rows
        ]
    )
