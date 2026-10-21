"""Folio's `/radicle` commands in Slack and Teams (Folio 5.4): search the docs, or ask the
docs chat (4.5) and get its answer with citations, with the asker's permissions."""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioVersion
from radicle.folio.services import access, chat, search
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.services.chat_commands import command
from radicle.platform.services.chat_previews import Preview, previewer

PAGE = re.compile(r"/folio/p/([0-9a-f-]{36})")

TOP = 5


def _absolute(url: str) -> str:
    return url if url.startswith("http") else get_settings().base_url.rstrip("/") + url


async def search_docs(db: AsyncSession, user: User, text: str) -> str:
    hits = await search.search(db, user, text, limit=TOP)
    if not hits:
        return f"Nothing in the docs matches “{text}”."
    lines = [f"• {h.title} ({h.space}): {_absolute(h.url)}\n  {h.snippet}" for h in hits]
    return "\n".join(lines)


async def ask_docs(db: AsyncSession, user: User, text: str) -> str:
    unavailable = await chat.unavailable(db)
    if unavailable:
        return unavailable
    session = await chat.create_session(db, user, title=text[: chat.TITLE_LENGTH])
    answer, sources = "", []
    async for event in await chat.ask(db, user, session, text):
        if event.name == "error":
            return str(event.data["detail"])
        if event.name == "done":
            answer = event.data["message"]["content"]
            sources = event.data["message"]["citations"]
    lines = [answer]
    for c in sources:
        outdated = " (outdated)" if c.get("outdated") else ""
        lines.append(f"[{c['n']}] {c['title']}{outdated}: {_absolute(c['url'])}")
    return "\n".join(lines)


async def preview_page(db: AsyncSession, user: User, url: str) -> Preview | None:
    """A Folio page link of this instance, if the person who pasted it can see the page."""
    base = get_settings().base_url.rstrip("/")
    found = PAGE.search(url) if url.startswith(base + "/") else None
    if found is None:
        return None
    node_id = uuid.UUID(found.group(1))
    node = await db.get(FolioNode, node_id)
    if node is None or node.deleted_at is not None or not await access.can_view(db, user, node_id):
        return None
    version = (
        await db.get(FolioVersion, node.published_version_id) if node.published_version_id else None
    )
    description = str((version.metadata_ if version else {}).get("description", ""))
    return Preview(node.title, description)


def register() -> None:
    command("search", "finds the 5 best pages")(search_docs)
    command("ask", "answers from the docs, with sources", slow=True)(ask_docs)
    previewer(preview_page)


register()  # the worker imports this module to run slow commands
