"""Ask the docs (Folio 4.5): an answer written only from the sections the reader may see,
each claim cited with [n] to its section, streamed as it is written.

When retrieval finds nothing, no model is asked: the answer says the docs don't cover it
and who to ask. Usage goes to platform's ai_calls without content; the messages
themselves stay in the asker's own sessions.
"""

import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.chat import ChatFeedback, ChatRole, FolioChatMessage, FolioChatSession
from radicle.folio.db.models import FolioSpace, FolioSpaceGrant, GranteeType
from radicle.folio.services import retrieval, search
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import ai

MAX_QUESTION = 2000
HISTORY_TURNS = 6
TITLE_LENGTH = 80
CITATION = re.compile(r"\[(\d{1,2})\]")
SPANISH = re.compile(r"[¿¡ñáéíóú]|\b(como|que|donde|cual|para|por|el|la|los|las|un|una)\b", re.I)

SYSTEM = """You answer questions about this organization's documentation in Radicle Folio.

Rules:
- Use only the numbered passages below. Never use outside knowledge, even if you know the answer.
- Cite every claim with its passage number in brackets right after it, like [1] or [2][3].
- If the passages don't answer the question, say plainly that the docs don't cover it and \
suggest asking {contact}. Don't guess.
- A passage marked OUTDATED may no longer be true: if you use it, say it may be out of date.
- Answer in the language of the question, briefly, in Markdown.

Passages:

{passages}"""


@dataclass(frozen=True)
class Event:
    """One server-sent event: `delta` with text, `done` with the saved answer, `error`."""

    name: str
    data: dict[str, Any]


FEATURE = "folio_chat"
OFF = {
    "no_provider": "The docs chat needs an AI provider with a chat model. An instance admin "
    "sets it in Admin, AI provider.",
    "off": "The docs chat is turned off for Folio in Admin, AI provider.",
}


def _off(cfg: ai.AiConfig) -> str | None:
    if not cfg.enabled or not cfg.chat_model:
        return OFF["no_provider"]
    if not cfg.features.get(FEATURE, True):
        return OFF["off"]
    return None


async def unavailable(db: AsyncSession) -> str | None:
    """Why the chat is off, or None when it is on."""
    return _off(await ai.load(db))


async def _require_available(db: AsyncSession) -> ai.AiConfig:
    cfg = await ai.load(db)
    off = _off(cfg)
    if off:
        raise ValidationFailed(
            off, code="no_chat_model", errors=[{"field": "provider", "message": "off"}]
        )
    return cfg


async def list_sessions(db: AsyncSession, user: User, limit: int = 30) -> list[FolioChatSession]:
    rows = await db.scalars(
        select(FolioChatSession)
        .where(FolioChatSession.user_id == user.id)
        .order_by(FolioChatSession.updated_at.desc(), FolioChatSession.id)
        .limit(limit)
    )
    return list(rows)


async def create_session(db: AsyncSession, user: User, title: str = "") -> FolioChatSession:
    session = FolioChatSession(user_id=user.id, title=title.strip()[:TITLE_LENGTH])
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> FolioChatSession:
    """Only its owner sees a session; anyone else gets a 404 as if it didn't exist."""
    session = await db.get(FolioChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise NotFound("No such chat session. List yours with GET /folio/chat/sessions.")
    return session


async def messages(db: AsyncSession, session: FolioChatSession) -> list[FolioChatMessage]:
    rows = await db.scalars(
        select(FolioChatMessage)
        .where(FolioChatMessage.session_id == session.id)
        .order_by(FolioChatMessage.created_at, FolioChatMessage.id)
    )
    return list(rows)


def _spanish(text: str) -> bool:
    return bool(SPANISH.search(text))


async def contact(
    db: AsyncSession, passages: list[retrieval.Passage], space_key: str | None
) -> str:
    """Who to ask when the docs don't say: the owner of the closest page, else the admins of
    the space asked about, else a Folio admin."""
    owner = next((p.owner for p in passages if p.owner), None)
    if owner:
        return f"@{owner.lstrip('@')}"
    key = space_key or (passages[0].space if passages else None)
    if key:
        handles = await db.scalars(
            select(User.handle)
            .join(FolioSpaceGrant, FolioSpaceGrant.grantee_id == User.id)
            .join(FolioSpace, FolioSpace.id == FolioSpaceGrant.space_id)
            .where(
                FolioSpace.key == key,
                FolioSpaceGrant.grantee_type == GranteeType.user,
                FolioSpaceGrant.permissions.contains(["admin"]),
            )
            .order_by(User.handle)
            .limit(2)
        )
        found = [f"@{h}" for h in handles]
        if found:
            return " or ".join(found)
    return "a Folio admin"


def _passages_text(passages: list[retrieval.Passage]) -> str:
    out = []
    for n, p in enumerate(passages, start=1):
        where = f"{p.title} > {p.section}" if p.section else p.title
        flag = " (OUTDATED)" if p.outdated else ""
        out.append(f"[{n}] {where}{flag}\n{p.text}")
    return "\n\n".join(out)


def citations(answer: str, passages: list[retrieval.Passage]) -> list[dict[str, Any]]:
    """The passages the answer actually cites, in the order it first cites them."""
    seen: list[int] = []
    for match in CITATION.finditer(answer):
        n = int(match.group(1))
        if 1 <= n <= len(passages) and n not in seen:
            seen.append(n)
    out = []
    for n in seen:
        p = passages[n - 1]
        out.append(
            {
                "n": n,
                "node_id": str(p.node_id),
                "version": p.version,
                "anchor": p.anchor,
                "title": p.title,
                "section": p.section,
                "url": p.url,
                "outdated": p.outdated,
            }
        )
    return out


def _not_covered(question: str, who: str) -> str:
    if _spanish(question):
        return f"No encontré esto en los docs. Pregúntale a {who.replace(' or ', ' o ')}."
    return f"I couldn't find this in the docs. Try asking {who}."


async def _history(db: AsyncSession, session: FolioChatSession) -> list[ai.Turn]:
    earlier = (await messages(db, session))[-HISTORY_TURNS:]
    return [ai.Turn(m.role.value, m.content) for m in earlier if m.content]


async def ask(
    db: AsyncSession,
    user: User,
    session: FolioChatSession,
    question: str,
    *,
    filters: search.Filters | None = None,
) -> AsyncIterator[Event]:
    """Save the question, then stream the answer: `delta` events and a final `done` with
    the saved message and its citations; `error` if the provider fails midway."""
    question = question.strip()
    if not question or len(question) > MAX_QUESTION:
        raise ValidationFailed(
            f"Ask a question of 1 to {MAX_QUESTION} characters.",
            errors=[{"field": "content", "message": "length"}],
        )
    cfg = await _require_available(db)
    turns = [*await _history(db, session), ai.Turn("user", question)]
    db.add(FolioChatMessage(session_id=session.id, role=ChatRole.user, content=question))
    if not session.title:
        session.title = question[:TITLE_LENGTH]
    session.updated_at = utcnow()
    await db.flush()
    passages = await retrieval.retrieve(db, user, question, filters=filters)
    who = await contact(db, passages, filters.space if filters else None)
    answer = FolioChatMessage(
        session_id=session.id,
        role=ChatRole.assistant,
        content="",
        citations=[],
        retrieval=[
            {"chunk_id": p.chunk_id, "node_id": str(p.node_id), "score": round(p.score, 6)}
            for p in passages
        ],
    )
    return _answer(db, cfg, user, answer, turns, passages, question, who)


async def _answer(
    db: AsyncSession,
    cfg: ai.AiConfig,
    user: User,
    answer: FolioChatMessage,
    turns: list[ai.Turn],
    passages: list[retrieval.Passage],
    question: str,
    who: str,
) -> AsyncIterator[Event]:
    if not passages:
        answer.content = _not_covered(question, who)
        yield Event("delta", {"text": answer.content})
    else:
        system = SYSTEM.format(contact=who, passages=_passages_text(passages))
        usage = ai.Usage()
        parts: list[str] = []
        try:
            async for piece in ai.stream(
                db, cfg, system, turns, app="folio", feature="chat", user=user, usage=usage
            ):
                parts.append(piece)
                yield Event("delta", {"text": piece})
        except ai.AiUnavailable as exc:
            yield Event("error", {"detail": exc.detail, "code": exc.code})
            return
        answer.content = "".join(parts).strip()
        answer.citations = citations(answer.content, passages)
        answer.input_tokens, answer.output_tokens = usage.input_tokens, usage.output_tokens
        answer.latency_ms = usage.latency_ms
    db.add(answer)
    await db.flush()
    yield Event("done", {"message": message_view(answer)})


def message_view(m: FolioChatMessage) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "role": m.role.value,
        "content": m.content,
        "citations": m.citations or [],
        "feedback": m.feedback.value if m.feedback else None,
        "created_at": m.created_at.isoformat() if m.created_at else utcnow().isoformat(),
    }


async def give_feedback(
    db: AsyncSession, user: User, message_id: uuid.UUID, value: ChatFeedback, note: str | None
) -> FolioChatMessage:
    message = await db.get(FolioChatMessage, message_id)
    session = await db.get(FolioChatSession, message.session_id) if message else None
    if message is None or session is None or session.user_id != user.id:
        raise NotFound("No such chat message among yours.")
    if message.role != ChatRole.assistant:
        raise ValidationFailed(
            "Feedback goes on an answer, not on a question.",
            errors=[{"field": "message", "message": "not an answer"}],
        )
    message.feedback = value
    message.feedback_note = (note or "").strip()[:1000] or None
    await db.flush()
    return message


@dataclass(frozen=True)
class Unanswered:
    question: str
    answer: str
    feedback: str | None
    feedback_note: str | None
    asked_at: Any


async def unanswered(db: AsyncSession, user: User, limit: int = 50) -> list[Unanswered]:
    """Folio admins: questions the docs didn't answer (no citation) or whose answer got a
    thumbs down, newest first, to know what to document."""
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()
    answer = FolioChatMessage
    asked = select(FolioChatMessage).subquery("asked")
    question = (
        select(asked.c.content)
        .where(
            asked.c.session_id == answer.session_id,
            asked.c.role == ChatRole.user,
            asked.c.created_at <= answer.created_at,
        )
        .order_by(asked.c.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(answer, question)
        .where(
            answer.role == ChatRole.assistant,
            or_(
                func.jsonb_array_length(answer.citations) == 0,
                answer.feedback == ChatFeedback.down,
            ),
        )
        .order_by(answer.created_at.desc(), answer.id)
        .limit(limit)
    )
    return [
        Unanswered(
            q or "",
            m.content,
            m.feedback.value if m.feedback else None,
            m.feedback_note,
            m.created_at,
        )
        for m, q in rows.all()
    ]
