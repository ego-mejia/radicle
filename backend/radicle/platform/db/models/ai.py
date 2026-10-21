import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class AiProvider(enum.StrEnum):
    none = "none"
    anthropic = "anthropic"
    openai = "openai"
    openai_compatible = "openai_compatible"
    ollama = "ollama"


class AiSettings(Base):
    """The instance's AI provider for chat and embeddings. A single row (id 1); the key is
    encrypted with RADICLE_SECRET_KEY."""

    __tablename__ = "ai_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_ai_settings_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[AiProvider] = mapped_column(
        _enum(AiProvider, "ai_provider"), default=AiProvider.none, server_default="none"
    )
    chat_model: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    base_url: Mapped[str | None] = mapped_column(Text)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
