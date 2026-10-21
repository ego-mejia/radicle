"""`/radicle` from Slack and Teams (Folio 5.4, ADR 0042): check the request's signature,
find who is asking in Radicle, and run the command an app registered with their
permissions.

Slack sends slash commands signed with the app's signing secret (`v0=` HMAC of
`v0:{timestamp}:{body}`); its user is matched by the email `users.info` returns. Teams
sends outgoing webhooks signed with HMAC-SHA256 of the body (base64), without the
person's email, so the first time Radicle answers with a link to connect the account.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import crypto
from radicle.platform.config import get_settings
from radicle.platform.db.models import (
    Integration,
    IntegrationIdentity,
    IntegrationKind,
    User,
)
from radicle.platform.errors import NotFound, Unauthorized, ValidationFailed
from radicle.platform.services import chat_notices, integrations, queue, safe_fetch

ASK_JOB = "platform_chat_command_later"
LINK_TTL = 15 * 60
SLACK_TOLERANCE = 300

Handler = Callable[[AsyncSession, User, str], Awaitable[str]]


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    run: Handler
    slow: bool  # answer later (Slack gives 3 seconds)


_commands: dict[str, Command] = {}


def command(name: str, help: str, *, slow: bool = False) -> Callable[[Handler], Handler]:
    """Register `/radicle <name> <text>`: `run(db, user, text)` returns the reply."""

    def register(fn: Handler) -> Handler:
        _commands[name] = Command(name, help, fn, slow)
        return fn

    return register


def usage() -> str:
    lines = [f"`/radicle {c.name} …` {c.help}" for c in _commands.values()]
    return "\n".join(lines) or "No commands are available."


# --- signatures ------------------------------------------------------------------------


def slack_signature(secret: str, timestamp: str, body: bytes) -> str:
    base = f"v0:{timestamp}:".encode() + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def check_slack(secret: str, headers: dict[str, str], body: bytes) -> None:
    timestamp = headers.get("x-slack-request-timestamp", "")
    if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > SLACK_TOLERANCE:
        raise Unauthorized("The Slack request is too old or has no timestamp.")
    given = headers.get("x-slack-signature", "")
    if not hmac.compare_digest(slack_signature(secret, timestamp, body), given):
        raise Unauthorized("The Slack signature doesn't match the signing secret.")


def teams_signature(secret: str, body: bytes) -> str:
    key = base64.b64decode(secret)
    return "HMAC " + base64.b64encode(hmac.new(key, body, hashlib.sha256).digest()).decode()


def check_teams(secret: str, headers: dict[str, str], body: bytes) -> None:
    if not hmac.compare_digest(teams_signature(secret, body), headers.get("authorization", "")):
        raise Unauthorized("The Teams signature doesn't match the outgoing webhook secret.")


# --- who is asking ---------------------------------------------------------------------


async def _linked(db: AsyncSession, integration: Integration, external_id: str) -> User | None:
    user_id = await db.scalar(
        select(IntegrationIdentity.user_id).where(
            IntegrationIdentity.integration_id == integration.id,
            IntegrationIdentity.external_id == external_id,
        )
    )
    user = await db.get(User, user_id) if user_id else None
    return user if user is not None and user.is_active else None


async def remember(
    db: AsyncSession, integration: Integration, external_id: str, user: User
) -> None:
    db.add(
        IntegrationIdentity(integration_id=integration.id, external_id=external_id, user_id=user.id)
    )
    await db.flush()


async def slack_user(db: AsyncSession, integration: Integration, slack_id: str) -> User | None:
    """The Radicle user with the Slack user's email; remembered after the first time."""
    found = await _linked(db, integration, slack_id)
    if found is not None:
        return found
    token = integrations.credentials(integration)["bot_token"]
    try:
        info = await chat_notices.slack_call(token, "users.info", {"user": slack_id})
    except safe_fetch.Blocked:
        return None
    email = (info.get("user", {}).get("profile", {}) or {}).get("email")
    if not email:
        return None
    user = await db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is not None:
        await remember(db, integration, slack_id, user)
    return user


def link_token(integration: Integration, external_id: str) -> str:
    claims = {"i": str(integration.id), "e": external_id, "x": int(time.time()) + LINK_TTL}
    return crypto.encrypt(json.dumps(claims))


def link_url(integration: Integration, external_id: str) -> str:
    base = get_settings().base_url.rstrip("/")
    return f"{base}/integrations/link?token={link_token(integration, external_id)}"


async def link(db: AsyncSession, user: User, token: str) -> Integration:
    """The signed-in person confirms they are this Slack or Teams user."""
    try:
        claims = json.loads(crypto.decrypt(token))
    except ValueError:
        raise ValidationFailed(
            "This link isn't valid. Run /radicle again in Slack or Teams for a new one.",
            errors=[{"field": "token", "message": "invalid"}],
        ) from None
    if claims["x"] < time.time():
        raise ValidationFailed(
            "This link expired after 15 minutes. Run /radicle again for a new one.",
            errors=[{"field": "token", "message": "expired"}],
        )
    integration = await integrations.get(db, uuid.UUID(claims["i"]))
    if await _linked(db, integration, claims["e"]) is None:
        await remember(db, integration, claims["e"], user)
    return integration


# --- running a command -----------------------------------------------------------------


def parse(text: str) -> tuple[Command | None, str]:
    name, _, rest = text.strip().partition(" ")
    return _commands.get(name.lower()), rest.strip()


async def run(db: AsyncSession, user: User, text: str) -> str:
    found, rest = parse(text)
    if found is None:
        return f"Try one of these:\n{usage()}"
    if not rest:
        return f"Add what to {found.name}: `/radicle {found.name} …`"
    try:
        return await found.run(db, user, rest)
    except ValidationFailed as exc:
        return exc.detail


async def slack_command(
    db: AsyncSession, integration: Integration, form: dict[str, str]
) -> dict[str, Any]:
    """The immediate reply to a slash command; slow commands answer on `response_url`."""
    user = await slack_user(db, integration, form.get("user_id", ""))
    if user is None:
        text = (
            "I couldn't find your Radicle account: your Slack email must match a Radicle "
            f"user. You can also connect it here: {link_url(integration, form.get('user_id', ''))}"
        )
        return {"response_type": "ephemeral", "text": text}
    found, rest = parse(form.get("text", ""))
    if found is not None and found.slow and rest:
        await queue.enqueue(
            db,
            ASK_JOB,
            user_id=str(user.id),
            text=form.get("text", ""),
            response_url=form.get("response_url", ""),
        )
        return {"response_type": "ephemeral", "text": f"On it: {rest}"}
    return {"response_type": "ephemeral", "text": await run(db, user, form.get("text", ""))}


@queue.handler(ASK_JOB)
async def answer_later(
    db: AsyncSession, user_id: str, text: str, response_url: str, **_: Any
) -> None:
    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not response_url.startswith("https://hooks.slack.com/"):
        return
    reply = await run(db, user, text)
    body = json.dumps({"response_type": "ephemeral", "text": reply}).encode()
    await safe_fetch.post(response_url, body, {"Content-Type": "application/json"})


async def teams_command(
    db: AsyncSession, integration: Integration, activity: dict[str, Any]
) -> dict[str, Any]:
    who = activity.get("from") or {}
    sender = str(who.get("aadObjectId") or who.get("id") or "")
    user = await _linked(db, integration, sender)
    if user is None:
        return {
            "type": "message",
            "text": f"Connect your Radicle account first: {link_url(integration, sender)}",
        }
    text = str(activity.get("text", ""))
    text = text.split("</at>", 1)[-1] if "</at>" in text else text
    return {"type": "message", "text": await run(db, user, text)}


async def handle(
    db: AsyncSession, integration_id: uuid.UUID, headers: dict[str, str], body: bytes
) -> dict[str, Any]:
    integration = await db.get(Integration, integration_id)
    if integration is None or not integration.active:
        raise NotFound("No active integration here. Check the URL in Admin, Integrations.")
    creds = integrations.credentials(integration)
    if integration.kind == IntegrationKind.slack:
        check_slack(creds["signing_secret"], headers, body)
        form = dict(parse_qsl(body.decode()))
        return await slack_command(db, integration, form)
    check_teams(creds["secret"], headers, body)
    return await teams_command(db, integration, json.loads(body))
