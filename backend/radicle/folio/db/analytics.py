"""Folio phase 5 analytics (5.9): who reads what, per day, and what people search without
finding it. One row per reader, page and day keeps the daily totals and unique counts cheap."""

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, utcnow


class FolioPageView(Base):
    __tablename__ = "folio_page_views"
    __table_args__ = (Index("ix_folio_page_views_day", "day"),)

    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    views: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")


class FolioSearchLog(Base):
    __tablename__ = "folio_search_logs"
    __table_args__ = (Index("ix_folio_search_logs_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    query: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)
    results_count: Mapped[int] = mapped_column(BigInteger)
    clicked_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folio_nodes.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
