"""Folio's docs chat (phase 4.5): each person's sessions and their messages. An assistant
message keeps the citations it gave and the chunks it was given, for feedback and for the
admin's list of questions the docs did not answer."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class ChatRole(enum.StrEnum):
    user = "user"
    assistant = "assistant"


class ChatFeedback(enum.StrEnum):
    up = "up"
    down = "down"


class FolioChatSession(Base):
    __tablename__ = "folio_chat_sessions"
    __table_args__ = (Index("ix_folio_chat_sessions_user", "user_id", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class FolioChatMessage(Base):
    __tablename__ = "folio_chat_messages"
    __table_args__ = (Index("ix_folio_chat_messages_session", "session_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folio_chat_sessions.id", ondelete="CASCADE")
    )
    role: Mapped[ChatRole] = mapped_column(_enum(ChatRole, "folio_chat_role"))
    content: Mapped[str] = mapped_column(Text)
    # [{n, node_id, version, anchor, title, section, url, outdated}]
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    # [{chunk_id, node_id, score}]: what retrieval handed the model
    retrieval: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    feedback: Mapped[ChatFeedback | None] = mapped_column(
        _enum(ChatFeedback, "folio_chat_feedback")
    )
    feedback_note: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
