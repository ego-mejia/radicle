import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.base import Base, _enum, utcnow


class Captcha(enum.StrEnum):
    altcha = "altcha"
    turnstile = "turnstile"
    hcaptcha = "hcaptcha"
    none = "none"


captcha_enum = _enum(Captcha, "captcha")


class InboxSettings(Base):
    """The public form of a project's inbox (/b/{slug})."""

    __tablename__ = "inbox_settings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    public_slug: Mapped[str] = mapped_column(CITEXT, unique=True)
    title: Mapped[str] = mapped_column(Text, default="")
    intro_md: Mapped[str] = mapped_column(Text, default="")
    thank_you_md: Mapped[str] = mapped_column(Text, default="")
    allowed_classifications: Mapped[list[str]] = mapped_column(ARRAY(Text))
    require_email: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_attachments: Mapped[bool] = mapped_column(Boolean, default=True)
    max_attachments: Mapped[int] = mapped_column(Integer, default=3)
    captcha: Mapped[Captcha] = mapped_column(captcha_enum, default=Captcha.altcha)
    # {"site_key": "...", "secret": "<encrypted>"} for turnstile and hcaptcha.
    captcha_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    auto_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class InboxSubmission(Base):
    """One accepted public submission, for rate limits. The IP is a salted daily hash."""

    __tablename__ = "inbox_submissions"
    __table_args__ = (Index("ix_inbox_submissions_ip", "ip_hash", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    ip_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class UsedChallenge(Base):
    """ALTCHA challenges already spent, so a solved one cannot be replayed."""

    __tablename__ = "used_challenges"

    challenge: Mapped[str] = mapped_column(Text, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
