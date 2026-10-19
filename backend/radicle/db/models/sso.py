import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.base import Base, utcnow


class AuthSource(enum.StrEnum):
    local = "local"
    oidc = "oidc"


class SsoProvider(Base):
    """An OpenID Connect provider (Google, Entra ID, Okta, Keycloak, Authentik...)."""

    __tablename__ = "sso_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    issuer_url: Mapped[str] = mapped_column(Text)
    client_id: Mapped[str] = mapped_column(Text)
    client_secret_encrypted: Mapped[str] = mapped_column(Text)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text))
    allowed_domains: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    auto_create_users: Mapped[bool] = mapped_column(Boolean, default=True)
    group_claim: Mapped[str | None] = mapped_column(Text)
    # {"radicle-backend": "<group id>"}
    group_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class InstanceSetting(Base):
    """Instance-wide switches, e.g. password_login_enabled."""

    __tablename__ = "instance_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
