"""Radi's answers: the configured LLM grounded on the usage guide, or the guide alone."""

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.services.assistant import config, guide, llm

Language = Literal["en", "es"]
LANGUAGE_NAMES = {"en": "English", "es": "Spanish"}
SYSTEM = """You are Radi, the small green helper inside Radicle, an open source ticket tracker \
for people and AI agents. Answer only questions about using Radicle, using the guide \
excerpts below. If they do not cover the question, say you are not sure and point to the \
closest section. Never invent features, buttons or settings.
Reply in {language}. Be brief and friendly: a few short sentences or a short numbered list. \
Write button and menu names in **bold**.

Guide sections: {toc}

Relevant excerpts:
{excerpts}"""
NOT_FOUND = {
    "en": "I could not find that in the guide. Try other words, like *create a project* or "
    "*board columns*.",
    "es": "No encontré eso en la guía. Prueba con otras palabras, como *crear un proyecto* o "
    "*columnas del board*.",
}
RELATED = {"en": "Related", "es": "Relacionado"}
UNAVAILABLE = {
    "en": "My AI is not available right now, so here is what the guide says.",
    "es": "Mi IA no está disponible ahora, así que te comparto lo que dice la guía.",
}


@dataclass
class Reply:
    answer: str
    mode: Literal["llm", "guide"]
    sources: list[str] = field(default_factory=list)
    notice: str | None = None


def _question(messages: list[llm.Message]) -> str:
    """The last question, plus the one before for short follow-ups ("and in Spanish?")."""
    asked = [m.content for m in messages if m.role == "user"]
    return " ".join(asked[-2:])


def from_guide(question: str, lang: Language) -> Reply:
    hits = guide.search(question, lang)
    if not hits:
        return Reply(NOT_FOUND[lang], "guide")
    best, others = hits[0], hits[1:]
    text = f"**{best.title}**\n\n{best.body}"
    if others:
        text += f"\n\n{RELATED[lang]}: " + ", ".join(f"*{s.title}*" for s in others)
    return Reply(text, "guide", [s.title for s in hits])


async def answer(
    db: AsyncSession, messages: list[llm.Message], lang: Language, *, admin: bool = False
) -> Reply:
    question = _question(messages)
    cfg = await config.load(db)
    if not cfg.enabled:
        return from_guide(question, lang)
    hits = guide.search(question, lang, limit=4)
    system = SYSTEM.format(
        language=LANGUAGE_NAMES[lang],
        toc=", ".join(guide.contents(lang)),
        excerpts="\n\n".join(f"## {s.title}\n{s.body}" for s in hits) or "(none matched)",
    )
    try:
        text = await llm.complete(cfg, system, messages[-12:])
    except llm.AssistantUnavailable as exc:
        reply = from_guide(question, lang)
        # Admins can fix the setup, so they see why; everyone else just gets the guide.
        reply.notice = exc.detail if admin else UNAVAILABLE[lang]
        return reply
    return Reply(text, "llm", [s.title for s in hits])
