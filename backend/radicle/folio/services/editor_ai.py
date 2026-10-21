"""AI in the editor (Folio 4.6): summarize a page, rewrite a selection and suggest the
publishing metadata. Everything is a proposal the person accepts or discards; nothing here
changes a page. Without a provider, or with AI off for Folio or the space, it is off."""

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioNodeLabel, FolioSpace, FolioVersion
from radicle.folio.services import access, catalogs, drafts, nodes
from radicle.folio.services.metadata import LABEL_RE
from radicle.platform.db.models import User
from radicle.platform.errors import ProblemError, ValidationFailed
from radicle.platform.services import ai

FEATURE = "folio_editor"
MAX_PAGE_CHARS = 24_000
MAX_SELECTION = 8_000
Mode = Literal["clearer", "shorter", "formal", "translate"]
Off = Literal["no_provider", "off_for_folio", "off_in_space"]


class AiOff(ProblemError):
    status = 409
    code = "ai_off"


def instance_off(cfg: ai.AiConfig) -> Off | None:
    """Why Folio's AI is off for the whole instance, or None."""
    if not cfg.enabled or not cfg.chat_model:
        return "no_provider"
    if not cfg.features.get(FEATURE, True):
        return "off_for_folio"
    return None


async def unavailable(db: AsyncSession, space: FolioSpace) -> Off | None:
    """Why the editor AI is off in this space, or None when it is on."""
    off = instance_off(await ai.load(db))
    if off is None and not space.ai_enabled:
        return "off_in_space"
    return off


REASONS: dict[Off, str] = {
    "no_provider": "No AI provider with a chat model is configured. An instance admin sets "
    "one in Admin, AI provider.",
    "off_for_folio": "The editor AI is turned off for Folio in Admin, AI provider.",
    "off_in_space": "The editor AI is turned off in this space. A space admin can turn it on "
    "in the space settings.",
}


async def _config(db: AsyncSession, node: FolioNode) -> ai.AiConfig:
    space = await db.get_one(FolioSpace, node.space_id)
    off = await unavailable(db, space)
    if off:
        raise AiOff(REASONS[off])
    return await ai.load(db)


async def _ask(
    db: AsyncSession, user: User, node: FolioNode, feature: str, system: str, prompt: str
) -> str:
    cfg = await _config(db, node)
    turns = [ai.Turn("user", prompt)]
    reply = await ai.chat(db, cfg, system, turns, app="folio", feature=feature, user=user)
    if not reply.text:
        raise ai.AiUnavailable("The AI answered with nothing. Try again.")
    return reply.text


async def _page_text(db: AsyncSession, user: User, node: FolioNode) -> str:
    """The draft for whoever may edit; the published version for everyone else."""
    if await access.may_edit(db, user, node):
        md = (await drafts.get_draft(db, node)).content_md
    else:
        version = (
            await db.get(FolioVersion, node.published_version_id)
            if node.published_version_id
            else None
        )
        md = version.content_md if version else ""
    if not md.strip():
        raise ValidationFailed(
            "The page is empty: write something before asking the AI.",
            errors=[{"field": "content", "message": "empty"}],
        )
    return md[:MAX_PAGE_CHARS]


async def summarize(db: AsyncSession, user: User, node_id: uuid.UUID) -> str:
    node = await nodes.get_node(db, user, node_id)
    text = await _page_text(db, user, node)
    system = (
        "You summarize internal documentation. Write 3 to 6 short bullet points in Markdown, "
        "in the language of the page. Use only what the page says; never add facts."
    )
    return await _ask(db, user, node, "summarize", system, f"# {node.title}\n\n{text}")


INSTRUCTIONS: dict[Mode, str] = {
    "clearer": "Rewrite it to be clearer and easier to read. Keep the meaning and language.",
    "shorter": "Rewrite it shorter, keeping every important point. Keep the language.",
    "formal": "Rewrite it in a more formal, professional tone. Keep the meaning and language.",
    "translate": "Translate it to {language}. Keep the Markdown formatting.",
}


async def rewrite(
    db: AsyncSession,
    user: User,
    node_id: uuid.UUID,
    text: str,
    mode: Mode,
    language: str | None = None,
) -> str:
    node = await nodes.get_node(db, user, node_id)
    await access.require_edit(db, user, node)
    if not text.strip():
        raise ValidationFailed(
            "Select the text to rewrite.", errors=[{"field": "text", "message": "empty"}]
        )
    if len(text) > MAX_SELECTION:
        raise ValidationFailed(
            f"Select at most {MAX_SELECTION} characters to rewrite.",
            errors=[{"field": "text", "message": "too long"}],
        )
    if mode == "translate" and not (language or "").strip():
        raise ValidationFailed(
            "Say which language to translate to, e.g. English.",
            errors=[{"field": "language", "message": "required"}],
        )
    system = (
        "You edit a passage of internal documentation. "
        + INSTRUCTIONS[mode].format(language=(language or "").strip())
        + " Answer with the new passage only, in Markdown, without quotes or comments."
    )
    return await _ask(db, user, node, f"rewrite_{mode}", system, text)


@dataclass(frozen=True)
class Suggestion:
    description: str | None
    labels: list[str]
    doc_type: str | None


async def _labels_in_use(db: AsyncSession, user: User) -> list[str]:
    visible = await access.node_filter(db, user)
    rows = await db.scalars(
        select(FolioNodeLabel.label)
        .join(FolioNode, FolioNode.id == FolioNodeLabel.node_id)
        .where(visible)
        .group_by(FolioNodeLabel.label)
        .order_by(func.count().desc(), FolioNodeLabel.label)
        .limit(40)
    )
    return list(rows)


def _json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise ai.AiUnavailable("The AI did not answer with suggestions. Try again.")
    return data


async def suggest_metadata(db: AsyncSession, user: User, node_id: uuid.UUID) -> Suggestion:
    """A description, labels and a document type for the publish dialog. Only values that
    pass the publishing rules come back; the person still decides."""
    node = await nodes.get_node(db, user, node_id)
    await access.require_edit(db, user, node)
    text = await _page_text(db, user, node)
    doc_types = await catalogs.active_keys(db, "doc-types")
    in_use = await _labels_in_use(db, user)
    system = (
        "You propose publishing metadata for an internal document. Answer only with JSON: "
        '{"description": "1 to 3 sentences, 40 to 400 characters, in the language of the '
        'page", "labels": ["1 to 5 lowercase labels with letters, digits, - or _"], '
        '"doc_type": "one of the given keys"}. Prefer labels already in use.'
    )
    prompt = (
        f"Document types: {', '.join(doc_types)}\n"
        f"Labels in use: {', '.join(in_use) or 'none yet'}\n\n# {node.title}\n\n{text}"
    )
    data = _json(await _ask(db, user, node, "suggest_metadata", system, prompt))
    description = str(data.get("description") or "").strip()
    raw = data.get("labels") if isinstance(data.get("labels"), list) else []
    labels = [str(x).strip().lower().lstrip("#") for x in raw or []]
    doc_type = data.get("doc_type")
    return Suggestion(
        description=description if 40 <= len(description) <= 400 else None,
        labels=[x for x in dict.fromkeys(labels) if LABEL_RE.fullmatch(x)][:5],
        doc_type=doc_type if doc_type in doc_types else None,
    )
