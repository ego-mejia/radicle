"""Build spec to tickets (Folio 4.3). A `build-spec` doc lists its deliverables either as
rows of a deliverables table (`# | Entregable | Incluye | Se acepta cuando`) or as
numbered level-3 headings (`### 4.1 Chat RAG`). Each one becomes a Docket task with a
link to its section and its acceptance criteria as a checklist; the link keeps the
deliverable's key, so running it again only creates the new ones."""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.docket_links import FolioTicketLink, TicketLinkKind
from radicle.folio.db.models import FolioDraft, FolioNode, FolioVersion
from radicle.folio.services import access
from radicle.folio.services.chunking import anchor_for, heading_text
from radicle.folio.services.ticket_links import page_path, upsert
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.errors import ValidationFailed

Node = dict[str, Any]
DOC_TYPE = "build-spec"
MAX_ITEMS = 50
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+(.+)$")
CRITERIA_SPLIT = re.compile(r"\s*(?:;|\n)\s*")

# Header names, folded to plain lowercase ASCII, in Spanish and English.
TITLE_COLS = {"entregable", "deliverable", "titulo", "title"}
KEY_COLS = {"#", "n", "no", "num", "id"}
DESCRIPTION_COLS = {"incluye", "includes", "descripcion", "description", "detalle"}
CRITERIA_COLS = {
    "se acepta cuando",
    "criterios",
    "criterios de aceptacion",
    "acceptance",
    "acceptance criteria",
    "accepted when",
    "done when",
}


@dataclass
class Item:
    key: str
    title: str
    description: str
    criteria: list[str]
    anchor: str | None


@dataclass
class ItemWithTicket:
    item: Item
    linked: bool = False
    ticket: docket.TicketSummary | None = None  # None when not linked, or you can't see it


@dataclass
class Choice:
    project: str
    keys: list[str] | None = None  # None: every deliverable without a ticket
    type: str = "task"
    area: str | None = None
    milestone: str | None = None
    tags: list[str] = field(default_factory=list)


def _fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", plain.strip().lower().rstrip(":"))


def _text(node: Node) -> str:
    if node.get("type") == "text":
        return str(node.get("text", ""))
    if node.get("type") == "hardBreak":
        return "\n"
    parts = [_text(child) for child in node.get("content", [])]
    joiner = "\n" if node.get("type") in ("tableCell", "tableHeader", "doc") else ""
    return joiner.join(parts).strip() if joiner else "".join(parts)


def _list_items(node: Node) -> list[str]:
    return [_text(item).strip() for item in node.get("content", []) if _text(item).strip()]


def _criteria(cell: str) -> list[str]:
    return [c for c in CRITERIA_SPLIT.split(cell) if c]


def _column(headers: list[str], names: set[str]) -> int | None:
    return next((i for i, h in enumerate(headers) if h in names), None)


def _from_table(table: Node, anchor: str | None) -> list[Item] | None:
    rows = table.get("content", [])
    if not rows:
        return None
    headers = [_fold(_text(cell)) for cell in rows[0].get("content", [])]
    title_col = _column(headers, TITLE_COLS)
    if title_col is None:
        return None
    key_col = _column(headers, KEY_COLS)
    desc_col = _column(headers, DESCRIPTION_COLS)
    crit_col = _column(headers, CRITERIA_COLS)
    items: list[Item] = []
    for n, row in enumerate(rows[1:], start=1):
        cells = [_text(cell) for cell in row.get("content", [])]

        def cell(col: int | None, cells: list[str] = cells) -> str:
            return cells[col].strip() if col is not None and col < len(cells) else ""

        title = cell(title_col)
        if not title:
            continue
        items.append(
            Item(
                key=cell(key_col) or str(n),
                title=title,
                description=cell(desc_col),
                criteria=_criteria(cell(crit_col)),
                anchor=anchor,
            )
        )
    return items


def detect(doc: Node) -> list[Item]:
    """The doc's deliverables: the first table with a deliverable column, or else its
    numbered level-3 headings with the text and lists under each."""
    taken: set[str] = set()
    anchor: str | None = None
    headed: list[Item] = []
    current: Item | None = None
    for node in doc.get("content", []):
        kind = node.get("type")
        if kind == "heading":
            level = int((node.get("attrs") or {}).get("level", 1))
            title = _text(node).strip()
            anchor = anchor_for(heading_text(node), taken)
            if level <= 3:
                current = None
            match = NUMBERED.match(title) if level == 3 else None
            if match:
                current = Item(match.group(1), match.group(2).strip(), "", [], anchor)
                headed.append(current)
        elif kind == "table":
            found = _from_table(node, anchor)
            if found:
                return _unique(found)
        elif current is not None and kind == "paragraph":
            text = _text(node).strip()
            current.description = "\n\n".join(p for p in (current.description, text) if p)
        elif current is not None and kind in ("taskList", "bulletList", "orderedList"):
            current.criteria += _list_items(node)
    return _unique(headed)


def _unique(items: list[Item]) -> list[Item]:
    seen: dict[str, Item] = {}
    for item in items[:MAX_ITEMS]:
        seen.setdefault(item.key, item)
    return list(seen.values())


async def _content(db: AsyncSession, user: User, node: FolioNode) -> tuple[Node, str | None]:
    """What the user sees of the doc (an editor's draft, else the published version) and
    its doc type."""
    if await access.may_edit(db, user, node):
        draft = await db.get(FolioDraft, node.id)
        if draft is not None:
            return draft.content_json, draft.metadata_.get("doc_type")
    if node.published_version_id is not None:
        version = await db.get(FolioVersion, node.published_version_id)
        if version is not None:
            return version.content_json, version.metadata_.get("doc_type")
    return {"type": "doc", "content": []}, None


async def items(db: AsyncSession, user: User, node: FolioNode) -> list[ItemWithTicket]:
    """The deliverables and, for each one already sent to Docket, its ticket as you see it."""
    doc, doc_type = await _content(db, user, node)
    if doc_type != DOC_TYPE:
        raise ValidationFailed(
            f"This doc's type is {doc_type or 'not set'}; only {DOC_TYPE} docs have "
            "deliverables. Set its type to build-spec and save.",
            code="not_a_build_spec",
            errors=[{"field": "doc_type", "message": "not build-spec"}],
        )
    links = {
        row.item_key: row
        for row in await db.scalars(
            select(FolioTicketLink).where(
                FolioTicketLink.node_id == node.id,
                FolioTicketLink.kind == TicketLinkKind.build_spec_item,
                FolioTicketLink.item_key.is_not(None),
            )
        )
    }
    seen = await docket.get_tickets_by_id(db, [r.ticket_id for r in links.values()], user)
    out = []
    for item in detect(doc):
        row = links.get(item.key)
        out.append(ItemWithTicket(item, row is not None, seen.get(row.ticket_id) if row else None))
    return out


def description(node: FolioNode, item: Item) -> str:
    url = get_settings().base_url.rstrip("/") + page_path(node, item.anchor)
    parts = [item.description] if item.description else []
    parts.append(f"From [{node.title} — {item.title}]({url}).")
    if item.criteria:
        parts.append("Acceptance criteria:\n\n" + "\n".join(f"- [ ] {c}" for c in item.criteria))
    return "\n\n".join(parts)


async def create_tickets(
    db: AsyncSession, user: User, node: FolioNode, choice: Choice, *, dry_run: bool = False
) -> list[ItemWithTicket]:
    """One Docket task per chosen deliverable that has none yet. With dry_run, nothing is
    created: the result lists what would be (linked=False, ticket=None)."""
    await access.require_edit(db, user, node)
    found = await items(db, user, node)
    known = {f.item.key for f in found}
    if choice.keys is not None:
        unknown = [k for k in choice.keys if k not in known]
        if unknown:
            raise ValidationFailed(
                f"Unknown deliverables: {', '.join(unknown)}. "
                f"GET /nodes/{node.id}/build-spec/items lists them.",
                errors=[{"field": "keys", "message": "unknown"}],
            )
    wanted = set(choice.keys) if choice.keys is not None else known
    todo = [f for f in found if f.item.key in wanted and not f.linked]
    if dry_run:
        return todo
    made = []
    for f in todo:
        ticket = await docket.create_ticket(
            db,
            docket.NewTicket(
                project=choice.project,
                title=f"{f.item.key} {f.item.title}"[:255],
                description_md=description(node, f.item),
                type=choice.type,
                area=choice.area,
                milestone=choice.milestone,
                tags=choice.tags,
            ),
            user,
        )
        await upsert(
            db,
            node,
            ticket.id,
            TicketLinkKind.build_spec_item,
            user,
            f.item.anchor,
            item_key=f.item.key,
        )
        made.append(ItemWithTicket(f.item, True, ticket))
    return made
