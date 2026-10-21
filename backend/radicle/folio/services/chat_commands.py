"""Folio's `/radicle` commands in Slack and Teams (Folio 5.4): search the docs, or ask the
docs chat (4.5) and get its answer with citations, with the asker's permissions."""

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import chat, search
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.services.chat_commands import command

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


def register() -> None:
    command("search", "finds the 5 best pages")(search_docs)
    command("ask", "answers from the docs, with sources", slow=True)(ask_docs)


register()  # the worker imports this module to run slow commands
