"""The glossary (Folio 4.6). The AI suggests terms and definitions from Verified docs, a
Folio admin approves, edits or rejects them, and readers only ever see approved terms."""

import json
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.glossary import FolioGlossaryTerm, TermStatus
from radicle.folio.db.models import FolioNode, FolioVersion, NodeStatus
from radicle.folio.services import access, editor_ai
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, NotFound, ValidationFailed
from radicle.platform.services import ai

TERM_MAX = 80
DEFINITION_MAX = 600
ALIASES_MAX = 10
SUGGEST_DOCS = 20
SUGGEST_CHARS = 1500


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


async def _admin(db: AsyncSession, user: User) -> None:
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()


@dataclass(frozen=True)
class Term:
    row: FolioGlossaryTerm
    source: FolioNode | None  # only when the reader may see it


async def list_terms(db: AsyncSession, user: User, status: TermStatus | None = None) -> list[Term]:
    """Approved terms for everyone; other statuses only for Folio admins."""
    if status not in (None, TermStatus.approved):
        await _admin(db, user)
    query = select(FolioGlossaryTerm).where(
        FolioGlossaryTerm.status == (status or TermStatus.approved)
    )
    return await with_sources(
        db, user, list(await db.scalars(query.order_by(FolioGlossaryTerm.term)))
    )


async def with_sources(db: AsyncSession, user: User, rows: list[FolioGlossaryTerm]) -> list[Term]:
    """Each term with its source page, left out when the user may not see it."""
    sources = {r.source_node_id for r in rows if r.source_node_id}
    visible: dict[uuid.UUID, FolioNode] = {}
    if sources:
        allowed = await access.node_filter(db, user)
        found = await db.scalars(select(FolioNode).where(FolioNode.id.in_(sources), allowed))
        visible = {n.id: n for n in found}
    return [Term(r, visible.get(r.source_node_id) if r.source_node_id else None) for r in rows]


@dataclass
class TermData:
    term: str | None = None
    definition: str | None = None
    aliases: list[str] | None = None
    source_node_id: uuid.UUID | None = None
    clear_source: bool = False
    status: TermStatus | None = None


def _clean(data: TermData, row: FolioGlossaryTerm) -> None:
    if data.term is not None:
        term = data.term.strip()
        if not 1 <= len(term) <= TERM_MAX:
            raise _invalid("term", f"A term is 1 to {TERM_MAX} characters.")
        row.term = term
    if data.definition is not None:
        definition = data.definition.strip()
        if not 1 <= len(definition) <= DEFINITION_MAX:
            raise _invalid("definition", f"A definition is 1 to {DEFINITION_MAX} characters.")
        row.definition = definition
    if data.aliases is not None:
        aliases = list(dict.fromkeys(a.strip() for a in data.aliases if a.strip()))
        if len(aliases) > ALIASES_MAX or any(len(a) > TERM_MAX for a in aliases):
            raise _invalid(
                "aliases", f"Up to {ALIASES_MAX} aliases of up to {TERM_MAX} characters."
            )
        row.aliases = aliases


async def _source(db: AsyncSession, user: User, node_id: uuid.UUID) -> uuid.UUID:
    if not await access.can_view(db, user, node_id):
        raise _invalid("source", f"Page {node_id} not found.")
    return node_id


async def _unique(db: AsyncSession, row: FolioGlossaryTerm) -> None:
    other = await db.scalar(
        select(FolioGlossaryTerm).where(
            FolioGlossaryTerm.term == row.term, FolioGlossaryTerm.id != row.id
        )
    )
    if other is not None:
        raise Conflict(
            f"'{row.term}' is already in the glossary ({other.status.value}). Edit that one.",
            code="term_exists",
        )


async def create_term(db: AsyncSession, user: User, data: TermData) -> FolioGlossaryTerm:
    """An admin's term goes straight to approved."""
    await _admin(db, user)
    if data.term is None or data.definition is None:
        raise _invalid("term", "Send a term and its definition.")
    row = FolioGlossaryTerm(id=uuid.uuid4(), status=TermStatus.approved, aliases=[])
    _clean(data, row)
    if data.source_node_id:
        row.source_node_id = await _source(db, user, data.source_node_id)
    await _unique(db, row)
    row.updated_by, row.updated_at = user.id, utcnow()
    db.add(row)
    await db.flush()
    return row


async def update_term(
    db: AsyncSession, user: User, term_id: uuid.UUID, data: TermData
) -> FolioGlossaryTerm:
    """Edit, approve or reject a term."""
    await _admin(db, user)
    row = await db.get(FolioGlossaryTerm, term_id)
    if row is None:
        raise NotFound(f"Glossary term {term_id} not found.", code="term_not_found")
    _clean(data, row)
    if data.clear_source:
        row.source_node_id = None
    elif data.source_node_id:
        row.source_node_id = await _source(db, user, data.source_node_id)
    if data.status is not None:
        row.status = data.status
    await _unique(db, row)
    row.updated_by, row.updated_at = user.id, utcnow()
    await db.flush()
    return row


def _suggested(text: str) -> list[dict[str, object]]:
    match = re.search(r"\[.*\]", text, re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, list):
        raise ai.AiUnavailable("The AI did not answer with terms. Try again.")
    return [d for d in data if isinstance(d, dict)]


async def suggest(db: AsyncSession, user: User) -> list[FolioGlossaryTerm]:
    """Ask the AI for terms in the newest Verified docs; new ones wait as suggestions."""
    await _admin(db, user)
    cfg = await ai.load(db)
    off = editor_ai.instance_off(cfg)
    if off:
        raise editor_ai.AiOff(editor_ai.REASONS[off])
    rows = (
        await db.execute(
            select(FolioNode.id, FolioNode.title, FolioVersion.content_md)
            .join(FolioVersion, FolioVersion.id == FolioNode.published_version_id)
            .where(FolioNode.status == NodeStatus.verified, FolioNode.deleted_at.is_(None))
            .order_by(FolioNode.updated_at.desc())
            .limit(SUGGEST_DOCS)
        )
    ).all()
    if not rows:
        raise ValidationFailed(
            "There are no Verified docs yet: the glossary is suggested from them.",
            errors=[{"field": "docs", "message": "none verified"}],
        )
    docs = "\n\n".join(
        f"[{n}] {title}\n{md[:SUGGEST_CHARS]}" for n, (_, title, md) in enumerate(rows, 1)
    )
    system = (
        "You build a glossary of an organization's own terms (products, acronyms, internal "
        "names) from its documentation. Skip common words. Answer only with JSON: "
        '[{"term": "...", "aliases": ["..."], "definition": "one or two sentences, in the '
        'language of the docs", "doc": n}] with at most 15 terms.'
    )
    reply = await ai.chat(
        db, cfg, system, [ai.Turn("user", docs)], app="folio", feature="glossary", user=user
    )
    known = {t.lower() for t in await db.scalars(select(FolioGlossaryTerm.term))}
    made: list[FolioGlossaryTerm] = []
    for item in _suggested(reply.text):
        term = str(item.get("term") or "").strip()
        definition = str(item.get("definition") or "").strip()
        if not (1 <= len(term) <= TERM_MAX and 1 <= len(definition) <= DEFINITION_MAX):
            continue
        if term.lower() in known:
            continue
        doc = item.get("doc")
        source = rows[doc - 1][0] if isinstance(doc, int) and 1 <= doc <= len(rows) else None
        raw = item.get("aliases")
        aliases = [str(a).strip() for a in raw if str(a).strip()] if isinstance(raw, list) else []
        row = FolioGlossaryTerm(
            id=uuid.uuid4(),
            term=term,
            definition=definition,
            aliases=[a for a in aliases if len(a) <= TERM_MAX][:ALIASES_MAX],
            source_node_id=source,
            status=TermStatus.suggested,
            updated_by=user.id,
            updated_at=utcnow(),
        )
        db.add(row)
        known.add(term.lower())
        made.append(row)
    await db.flush()
    return made
