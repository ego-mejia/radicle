"""Whiteboards (Folio 3.5): an Excalidraw scene drawn together, as a node of kind
whiteboard. The format is in docs/folio/whiteboards.md.

The scene lives in the node's Y.Doc as `Y.Map("elements")`, each element under its id,
so people who move different elements never overwrite each other. The room keeps
folio_whiteboards as its JSON read, and the text of its elements goes to search.
"""

from typing import Any

import pycrdt
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, NodeKind
from radicle.folio.db.whiteboards import FolioWhiteboard
from radicle.platform.db.models import utcnow
from radicle.platform.errors import ValidationFailed

ELEMENTS = "elements"
MAX_ELEMENTS = 10_000


def require_whiteboard(node: FolioNode) -> None:
    if node.kind != NodeKind.whiteboard:
        raise ValidationFailed(
            f"'{node.title}' is not a whiteboard. Whiteboards are created with kind whiteboard.",
            errors=[{"field": "node", "message": "not a whiteboard"}],
        )


def elements_map(doc: pycrdt.Doc[Any]) -> pycrdt.Map[Any]:
    found: pycrdt.Map[Any] = doc.get(ELEMENTS, type=pycrdt.Map)
    return found


def _usable(element: Any) -> bool:
    return (
        isinstance(element, dict)
        and isinstance(element.get("id"), str)
        and isinstance(element.get("type"), str)
        and not element.get("isDeleted")
    )


def read(doc: pycrdt.Doc[Any]) -> list[dict[str, Any]]:
    """The scene's elements in drawing order, deleted and malformed ones left out."""
    elements = [e for e in (elements_map(doc).to_py() or {}).values() if _usable(e)]
    # Excalidraw orders by fractional index; elements without one go first, by id.
    elements.sort(key=lambda e: (str(e.get("index") or ""), e["id"]))
    return elements[:MAX_ELEMENTS]


def from_elements(elements: list[dict[str, Any]]) -> pycrdt.Doc[Any]:
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    target = elements_map(doc)
    with doc.transaction():
        for element in elements:
            if _usable(element):
                target[element["id"]] = element
    return doc


def text_of(elements: list[dict[str, Any]]) -> str:
    """What the scene says: its texts and frame names, one per line."""
    lines = []
    for e in elements:
        value = e.get("text") if e["type"] == "text" else e.get("name")
        if isinstance(value, str) and value.strip():
            lines.append(value.strip())
    return "\n".join(lines)


async def get(db: AsyncSession, node: FolioNode) -> FolioWhiteboard:
    """The node's scene, empty the first time."""
    require_whiteboard(node)
    found = await db.get(FolioWhiteboard, node.id)
    if found is None:
        found = FolioWhiteboard(node_id=node.id, elements=[], text="", updated_at=utcnow())
        db.add(found)
        await db.flush()
    return found


async def save(db: AsyncSession, node: FolioNode, doc: pycrdt.Doc[Any]) -> bool:
    """Keep folio_whiteboards in step with the Y.Doc; search follows when the text
    changes. Returns whether anything changed."""
    row = await get(db, node)
    elements = read(doc)
    if row.elements == elements:
        return False
    text = text_of(elements)
    reindex = text != row.text
    row.elements, row.text, row.updated_at = elements, text, utcnow()
    await db.flush()
    if reindex:
        from radicle.folio.services import rag  # rag reads this module's rows

        await rag.schedule(db, [node.id])
    return True
