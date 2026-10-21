"""Slack and Teams (Folio 5.4, shared with Docket; ADR 0042): the integrations an instance
admin sets up, their credentials and the channels that hear each public event.

Slack: a bot token (`xoxb-…`) for `chat.postMessage`, `users.info` and `chat.unfurl`, and
the app's signing secret to check slash commands and events. Teams: each channel's
incoming webhook URL for notices, and the outgoing webhook's secret to check commands.
"""

import base64
import binascii
import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.db.models import Integration, IntegrationKind, User
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import events, safe_fetch


@dataclass(frozen=True)
class Route:
    """Which events a channel hears: `channel` is a Slack channel id (C0123…) or, in
    Teams, the channel's incoming webhook URL (kept encrypted)."""

    channel: str
    events: list[str] = field(default_factory=list)  # empty: every event
    filter: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IntegrationData:
    kind: IntegrationKind
    name: str
    # None keeps the stored credentials (updates); a dict replaces them.
    credentials: dict[str, str] | None
    notices: list[Route] | None = None  # None keeps the routes
    active: bool = True


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


def _check_credentials(kind: IntegrationKind, creds: dict[str, str]) -> dict[str, str]:
    if kind == IntegrationKind.slack:
        if not creds.get("bot_token", "").startswith("xoxb-"):
            raise _invalid("credentials", "Slack needs the bot token, which starts with xoxb-.")
        if not creds.get("signing_secret"):
            raise _invalid(
                "credentials", "Slack needs the app's signing secret (Basic Information)."
            )
        return {"bot_token": creds["bot_token"], "signing_secret": creds["signing_secret"]}
    try:
        base64.b64decode(creds.get("secret", ""), validate=True)
    except binascii.Error:
        raise _invalid("credentials", "The Teams outgoing webhook secret is base64.") from None
    if not creds.get("secret"):
        raise _invalid("credentials", "Teams needs the secret its outgoing webhook shows once.")
    return {"secret": creds["secret"]}


async def _check_routes(kind: IntegrationKind, routes: list[Route]) -> list[dict[str, Any]]:
    known = events.public_events()
    out = []
    for n, route in enumerate(routes):
        unknown = sorted(set(route.events) - set(known))
        if unknown:
            raise _invalid(
                f"notices[{n}].events",
                f"Unknown events: {', '.join(unknown)}. Valid ones: {', '.join(known)}.",
            )
        channel = route.channel.strip()
        if kind == IntegrationKind.slack:
            if not channel:
                raise _invalid(f"notices[{n}].channel", "Give the Slack channel id (C0123…).")
            target = channel
        else:
            try:
                await safe_fetch.check(channel)
            except safe_fetch.Blocked as exc:
                raise _invalid(f"notices[{n}].channel", exc.detail) from None
            target = crypto.encrypt(channel)
        out.append({"channel": target, "events": sorted(set(route.events)), "filter": route.filter})
    return out


def credentials(integration: Integration) -> dict[str, str]:
    loaded: dict[str, str] = json.loads(crypto.decrypt(integration.credentials_encrypted))
    return loaded


def routes(integration: Integration) -> list[Route]:
    """The routes with each channel readable (Teams URLs decrypted)."""
    out = []
    for r in integration.config.get("notices", []):
        channel = r["channel"]
        if integration.kind == IntegrationKind.teams:
            channel = crypto.decrypt(channel)
        out.append(Route(channel, list(r.get("events", [])), dict(r.get("filter", {}))))
    return out


def view(integration: Integration) -> dict[str, Any]:
    """For admins and the audit log: never a secret, and Teams URLs only by their host."""
    shown = []
    for r in routes(integration):
        channel = r.channel
        if integration.kind == IntegrationKind.teams:
            channel = urlsplit(channel).netloc + "/…"
        shown.append({"channel": channel, "events": r.events, "filter": r.filter})
    return {
        "id": str(integration.id),
        "kind": integration.kind.value,
        "name": integration.name,
        "active": integration.active,
        "notices": shown,
    }


async def create(db: AsyncSession, admin: User, data: IntegrationData) -> Integration:
    if not data.name.strip():
        raise _invalid("name", "Give the integration a name, e.g. the Slack workspace.")
    if data.credentials is None:
        raise _invalid("credentials", "Send the credentials the integration needs.")
    creds = _check_credentials(data.kind, data.credentials)
    integration = Integration(
        kind=data.kind,
        name=data.name.strip(),
        credentials_encrypted=crypto.encrypt(json.dumps(creds)),
        config={"notices": await _check_routes(data.kind, data.notices or [])},
        active=data.active,
        created_by=admin.id,
    )
    db.add(integration)
    await db.flush()
    return integration


async def update(db: AsyncSession, integration: Integration, data: IntegrationData) -> Integration:
    if not data.name.strip():
        raise _invalid("name", "Give the integration a name, e.g. the Slack workspace.")
    integration.name, integration.active = data.name.strip(), data.active
    if data.credentials is not None:
        creds = _check_credentials(integration.kind, data.credentials)
        integration.credentials_encrypted = crypto.encrypt(json.dumps(creds))
    if data.notices is not None:
        notices = await _check_routes(integration.kind, data.notices)
        integration.config = {**integration.config, "notices": notices}
    await db.flush()
    return integration


async def get(db: AsyncSession, integration_id: uuid.UUID) -> Integration:
    integration = await db.get(Integration, integration_id)
    if integration is None:
        raise NotFound("Integration not found. List them with GET /api/v1/integrations.")
    return integration


async def list_all(db: AsyncSession) -> list[Integration]:
    return list(await db.scalars(select(Integration).order_by(Integration.name)))
