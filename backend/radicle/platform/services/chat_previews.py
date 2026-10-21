"""Link previews in Slack (Folio 5.4, ADR 0042): when someone pastes a Radicle link, Slack
sends `link_shared` and Radicle unfurls it, only if that person's linked Radicle account
can see what the link shows. Apps register a previewer per kind of link."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import Integration, User
from radicle.platform.services import chat_commands, chat_notices, integrations, queue

UNFURL_JOB = "platform_unfurl_links"


@dataclass(frozen=True)
class Preview:
    title: str
    text: str


Previewer = Callable[[AsyncSession, User, str], Awaitable[Preview | None]]
_previewers: list[Previewer] = []


def previewer(fn: Previewer) -> Previewer:
    """`fn(db, user, url)` returns a preview of a link it knows and the user may see."""
    if fn not in _previewers:
        _previewers.append(fn)
    return fn


async def preview(db: AsyncSession, user: User, url: str) -> Preview | None:
    for fn in _previewers:
        found = await fn(db, user, url)
        if found is not None:
            return found
    return None


async def slack_event(
    db: AsyncSession, integration: Integration, doc: dict[str, Any]
) -> dict[str, Any]:
    """Answer Slack's Events API: the URL check, and `link_shared` (later, in a job)."""
    if doc.get("type") == "url_verification":
        return {"challenge": doc.get("challenge", "")}
    event = doc.get("event") or {}
    if doc.get("type") == "event_callback" and event.get("type") == "link_shared":
        await queue.enqueue(
            db,
            UNFURL_JOB,
            integration_id=str(integration.id),
            slack_user=str(event.get("user", "")),
            channel=str(event.get("channel", "")),
            ts=str(event.get("message_ts", "")),
            urls=[str(link.get("url", "")) for link in event.get("links", [])][:5],
        )
    return {"ok": True}


@queue.handler(UNFURL_JOB)
async def unfurl(
    db: AsyncSession,
    integration_id: str,
    slack_user: str,
    channel: str,
    ts: str,
    urls: list[str],
    **_: Any,
) -> None:
    integration = await db.get(Integration, integration_id)
    if integration is None or not integration.active:
        return
    user = await chat_commands.slack_user(db, integration, slack_user)
    if user is None:
        return  # nobody to check access for: nothing is shown
    unfurls = {}
    for url in urls:
        found = await preview(db, user, url)
        if found is not None:
            unfurls[url] = {"title": found.title, "title_link": url, "text": found.text}
    if unfurls:
        token = integrations.credentials(integration)["bot_token"]
        body = {"channel": channel, "ts": ts, "unfurls": unfurls}
        await chat_notices.slack_call(token, "chat.unfurl", body)
