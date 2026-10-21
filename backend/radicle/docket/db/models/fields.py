import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.docket.db.models.projects import TicketType, ticket_type_enum
from radicle.platform.db.models.base import Base, _enum, utcnow


class CustomFieldType(enum.StrEnum):
    text = "text"
    number = "number"
    date = "date"
    select = "select"
    checkbox = "checkbox"
    user = "user"
    url = "url"


custom_field_type_enum = _enum(CustomFieldType, "custom_field_type")


class CustomFieldDefinition(Base):
    __tablename__ = "custom_field_definitions"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_custom_fields_project_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    field_type: Mapped[CustomFieldType] = mapped_column(custom_field_type_enum)
    # select: [{"value": "prod", "label": "Prod", "color": "#..."}]; empty for other types.
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    applies_to_types: Mapped[list[TicketType]] = mapped_column(ARRAY(ticket_type_enum))
    # None means every area.
    applies_to_area_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    template_ref: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
