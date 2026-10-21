import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.base import Base, _enum, utcnow


class BoardKind(enum.StrEnum):
    kanban = "kanban"
    scrum = "scrum"


class WipMode(enum.StrEnum):
    soft = "soft"
    hard = "hard"


class Swimlane(enum.StrEnum):
    none = "none"
    area = "area"
    assignee = "assignee"
    priority = "priority"
    milestone = "milestone"
    parent = "parent"
    type = "type"


board_kind_enum = _enum(BoardKind, "board_kind")
wip_mode_enum = _enum(WipMode, "wip_mode")
swimlane_enum = _enum(Swimlane, "swimlane")


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Null when the source is a filter over several projects.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[BoardKind] = mapped_column(board_kind_enum, default=BoardKind.kanban)
    source_rql: Mapped[str] = mapped_column(Text)
    # [{"name": "Review", "status_ids": ["..."], "categories": ["in_progress"], "wip_limit": 3}]
    columns: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    wip_mode: Mapped[WipMode] = mapped_column(wip_mode_enum, default=WipMode.soft)
    swimlane_by: Mapped[Swimlane] = mapped_column(swimlane_enum, default=Swimlane.none)
    card_fields: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    done_window_days: Mapped[int] = mapped_column(Integer, default=14)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class BoardQuickFilter(Base):
    __tablename__ = "board_quick_filters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    rql: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
