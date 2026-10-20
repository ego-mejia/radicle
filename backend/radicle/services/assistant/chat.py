"""Radi's answers: the configured LLM grounded on the usage guide, or the guide alone."""

import re
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.services.assistant import config, guide, llm, tours

Language = Literal["en", "es"]
LANGUAGE_NAMES = {"en": "English", "es": "Spanish"}
SYSTEM = """You are Radi, the small green helper inside Radicle, an open source ticket tracker \
for people and AI agents. Answer only questions about using Radicle, from the usage guide \
below: it is complete, so if it does not mention a feature, Radicle does not have it. Say so \
plainly and offer the closest thing the guide does describe (for example, projects cannot be \
deleted but can be archived). Never invent features, buttons or settings.
Reply in the language of the user's last message ({language} when unsure), in your text and \
in every tour step. Be brief and friendly: a few short sentences or a short numbered list. \
Write button and menu names in **bold**.

Usage guide:
{guide}

Whenever the user asks how to do something in Radicle ("how do I...", "where is...", \
"show me...", "cómo...", "dónde...", "muéstrame..."), you must also call show_me: open the \
right page or dialog with click steps, then point at each part they need and explain it. \
Still answer in text too. The app may be in another language, so describe buttons by what \
they do instead of quoting their labels; the tour highlights them. Use only these targets:
{targets}"""
NOT_FOUND = {
    "en": "I could not find that in the guide. Try other words, like *create a project* or "
    "*board columns*.",
    "es": "No encontré eso en la guía. Prueba con otras palabras, como *crear un proyecto* o "
    "*columnas del board*.",
}
RELATED = {"en": "Related", "es": "Relacionado"}
ANYTHING_ELSE = {
    "en": "Happy to help! What else would you like to do in Radicle?",
    "es": "¡Con gusto! ¿Qué más quieres hacer en Radicle?",
}
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
    tour: list[tours.Step] = field(default_factory=list)
    # Guide tours wait for "Show me"; the model's tours start right away.
    autoplay: bool = False


def _asked(messages: list[llm.Message]) -> list[str]:
    return [m.content for m in messages if m.role == "user"]


def from_guide(question: str, lang: Language) -> Reply:
    if not guide.terms(question):  # "ok", "thanks", "n": nothing to look up
        return Reply(ANYTHING_ELSE[lang], "guide")
    hits = guide.search(question, lang)
    if not hits:
        return Reply(NOT_FOUND[lang], "guide")
    best, others = hits[0], hits[1:]
    text = f"**{best.title}**\n\n{best.body}"
    if others:
        text += f"\n\n{RELATED[lang]}: " + ", ".join(f"*{s.title}*" for s in others)
    return Reply(text, "guide", [s.title for s in hits], tour=tours.guide_tour(best.key, lang))


LET_ME_SHOW = {"en": "Let me show you.", "es": "Te muestro."}
SPANISH = re.compile(r"[¿¡ñáéíóú]|\b(como|que|donde|muestrame|quiero|puedo|hago|creo)\b", re.I)
HOW_TO = re.compile(r"\b(how|where|show|c[oó]mo|d[oó]nde|mu[eé]str|ens[eé][nñ])", re.IGNORECASE)


async def answer(
    db: AsyncSession, messages: list[llm.Message], lang: Language, *, admin: bool = False
) -> Reply:
    asked = _asked(messages)
    question = asked[-1] if asked else ""
    cfg = await config.load(db)
    if not cfg.enabled:
        return from_guide(question, lang)
    # The model sees the conversation; the excerpts also cover the previous question,
    # so short follow-ups ("and for bugs?") keep their context.
    hits = guide.search(" ".join(asked[-2:]), lang, limit=4)
    system = SYSTEM.format(
        language=LANGUAGE_NAMES[lang], guide=guide.full_text(lang), targets=tours.catalog()
    )
    try:
        done = await llm.converse(cfg, system, messages[-12:], tours.SHOW_ME)
    except llm.AssistantUnavailable as exc:
        reply = from_guide(question, lang)
        # Admins can fix the setup, so they see why; everyone else just gets the guide.
        reply.notice = exc.detail if admin else UNAVAILABLE[lang]
        return reply
    steps = tours.clean((done.tool_input or {}).get("steps"))
    # Models often call the tool without a word; greet in the language the user wrote in.
    asked_in: Language = "es" if SPANISH.search(question) else lang
    text = done.text or (LET_ME_SHOW[asked_in] if steps else "")
    if steps:
        return Reply(text, "llm", [s.title for s in hits], tour=steps, autoplay=True)
    # The model did not offer a walkthrough: offer the guide's when a how-to was asked.
    fallback = tours.guide_tour(hits[0].key, lang) if hits and HOW_TO.search(question) else []
    return Reply(text, "llm", [s.title for s in hits], tour=fallback)
