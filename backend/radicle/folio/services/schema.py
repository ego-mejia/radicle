"""Folio's document schema (Folio 1.2): the blocks of phase 1 as TipTap JSON, validated on
the server. The web editor mirrors it in `frontend/src/features/folio/editor/schema.ts`.

A document is `{"type": "doc", "content": [block, ...]}`. Every node has a `type`, maybe
`attrs` and `content`; text nodes have `text` and maybe `marks`. Unknown types, attributes
or children are rejected with the JSON path of the first problem.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from radicle.platform.errors import ValidationFailed

MAX_DEPTH = 40
MAX_NODES = 20_000

INLINE = "inline"
BLOCK = "block"


@dataclass(frozen=True)
class Attr:
    kind: type | tuple[type, ...]
    choices: tuple[Any, ...] = ()
    required: bool = False
    minimum: int | None = None
    maximum: int | None = None
    max_length: int = 2000


@dataclass(frozen=True)
class NodeSpec:
    group: str  # "block" or "inline"
    content: tuple[str, ...] = ()  # allowed child types or groups
    attrs: dict[str, Attr] = field(default_factory=dict)
    min_children: int = 0
    max_children: int | None = None
    leaf_text: bool = False  # content is text only (code blocks)
    # Extra checks for attributes a simple rule can't describe (lists of rows or items).
    check: Callable[[str, dict[str, Any]], None] | None = None


_STR = Attr(str)
_OPT_STR = Attr((str, type(None)))
_ID = Attr((str, type(None)), max_length=200)
PANEL_KINDS = ("info", "tip", "warning", "error", "note")
STATUS_COLORS = ("grey", "blue", "green", "yellow", "red", "purple")
COLUMN_LAYOUTS = ("two", "three", "sidebar_left", "sidebar_right")
IMAGE_SIZES = ("small", "medium", "large", "full")
ALIGNS = ("left", "center", "right")

VISUAL_FORMATS = ("svg", "html")
CHART_KINDS = ("bar", "line", "area", "pie")
DIAGRAM_LANGUAGES = ("mermaid",)
MAX_VISUAL = 512 * 1024  # bytes of SVG or HTML (UTF-8)
MAX_CHART_ROWS = 200
MAX_CHART_COLUMNS = 10
MAX_TIMELINE_ITEMS = 100


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_chart(path: str, attrs: dict[str, Any]) -> None:
    """data is rows: the first names the columns, the others hold a label and numbers."""
    rows = attrs.get("data")
    here = f"{path}.attrs.data"
    if not isinstance(rows, list) or len(rows) < 2:
        raise SchemaError(here, "needs a header row and at least one row of values")
    if len(rows) > MAX_CHART_ROWS:
        raise SchemaError(here, f"has at most {MAX_CHART_ROWS} rows")
    width = len(rows[0]) if isinstance(rows[0], list) else 0
    if not 2 <= width <= MAX_CHART_COLUMNS:
        raise SchemaError(here, f"rows have 2 to {MAX_CHART_COLUMNS} columns")
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != width:
            raise SchemaError(f"{here}[{i}]", f"every row has {width} cells")
        for j, cell in enumerate(row):
            label = i == 0 or j == 0
            ok = isinstance(cell, str) and len(cell) <= 200 if label else _number(cell)
            if not ok:
                raise SchemaError(
                    f"{here}[{i}][{j}]", "must be a label" if label else "must be a number"
                )


def _check_timeline(path: str, attrs: dict[str, Any]) -> None:
    items = attrs.get("items")
    here = f"{path}.attrs.items"
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_TIMELINE_ITEMS:
        raise SchemaError(here, f"has 1 to {MAX_TIMELINE_ITEMS} items")
    limits = {"date": 40, "title": 200, "text": 1000}
    for i, item in enumerate(items):
        if not isinstance(item, dict) or set(item) - set(limits) or not item.get("title"):
            raise SchemaError(f"{here}[{i}]", "items are {date, title, text} with a title")
        for key, value in item.items():
            if not isinstance(value, str) or len(value) > limits[key]:
                raise SchemaError(f"{here}[{i}].{key}", f"is text up to {limits[key]}")


def _check_embed(path: str, attrs: dict[str, Any]) -> None:
    if not str(attrs.get("url", "")).startswith(("https://", "http://")):
        raise SchemaError(f"{path}.attrs.url", "embeds take http or https links")


def _check_database_view(path: str, attrs: dict[str, Any]) -> None:
    try:
        uuid.UUID(str(attrs.get("database")))
    except ValueError:
        raise SchemaError(f"{path}.attrs.database", "must be a database's id (a uuid)") from None


def _check_visual(path: str, attrs: dict[str, Any]) -> None:
    if not str(attrs.get("description", "")).strip():
        raise SchemaError(
            f"{path}.attrs.description",
            "a visual needs a description: it is the alt text and what search reads",
        )


NODES: dict[str, NodeSpec] = {
    "paragraph": NodeSpec(BLOCK, (INLINE,)),
    "heading": NodeSpec(
        BLOCK,
        (INLINE,),
        {"level": Attr(int, (1, 2, 3, 4), required=True), "id": _ID},
    ),
    "bulletList": NodeSpec(BLOCK, ("listItem",), min_children=1),
    "orderedList": NodeSpec(
        BLOCK, ("listItem",), {"start": Attr(int, minimum=0, maximum=100_000)}, min_children=1
    ),
    "listItem": NodeSpec("list", (BLOCK,), min_children=1),
    "taskList": NodeSpec(BLOCK, ("taskItem",), min_children=1),
    "taskItem": NodeSpec("list", (BLOCK,), {"checked": Attr(bool)}, min_children=1),
    # An action item (Folio 2.4): its id is stable, so Mis tareas can find it again.
    "actionItem": NodeSpec(
        BLOCK,
        (INLINE,),
        {
            "id": Attr(str, required=True, max_length=64),
            "done": Attr(bool),
            "assignee": Attr((str, type(None)), max_length=64),
            "due": Attr((str, type(None)), max_length=10),
        },
    ),
    "blockquote": NodeSpec(BLOCK, (BLOCK,), min_children=1),
    "codeBlock": NodeSpec(BLOCK, attrs={"language": _OPT_STR}, leaf_text=True),
    "horizontalRule": NodeSpec(BLOCK),
    "table": NodeSpec(BLOCK, ("tableRow",), min_children=1),
    "tableRow": NodeSpec("row", ("tableCell", "tableHeader"), min_children=1),
    "tableCell": NodeSpec(
        "cell",
        (BLOCK,),
        {
            "colspan": Attr(int, minimum=1, maximum=50),
            "rowspan": Attr(int, minimum=1, maximum=500),
            "colwidth": Attr((list, type(None))),
            "background": _OPT_STR,
        },
        min_children=1,
    ),
    "panel": NodeSpec(BLOCK, (BLOCK,), {"kind": Attr(str, PANEL_KINDS, required=True)}, 1),
    "expand": NodeSpec(BLOCK, (BLOCK,), {"title": Attr(str, max_length=200)}, min_children=1),
    "columns": NodeSpec(
        BLOCK,
        ("column",),
        {"layout": Attr(str, COLUMN_LAYOUTS, required=True)},
        min_children=2,
        max_children=3,
    ),
    "column": NodeSpec("column", (BLOCK,), min_children=1),
    "tableOfContents": NodeSpec(BLOCK),
    "childPages": NodeSpec(BLOCK),
    "image": NodeSpec(
        BLOCK,
        attrs={
            "assetId": _OPT_STR,
            "src": _OPT_STR,
            "alt": _OPT_STR,
            "caption": _OPT_STR,
            "size": Attr(str, IMAGE_SIZES),
            "align": Attr(str, ALIGNS),
        },
    ),
    "file": NodeSpec(
        BLOCK,
        attrs={
            "assetId": Attr(str, required=True),
            "name": _STR,
            "mimeType": _OPT_STR,
            "size": Attr((int, type(None)), minimum=0),
        },
    ),
    "video": NodeSpec(BLOCK, attrs={"assetId": _OPT_STR, "src": _OPT_STR, "caption": _OPT_STR}),
    # Folio 3.3: SVG or HTML shown in a sandboxed iframe, with a required description.
    "visual": NodeSpec(
        BLOCK,
        attrs={
            "format": Attr(str, VISUAL_FORMATS, required=True),
            "code": Attr(str, required=True, max_length=MAX_VISUAL),
            "title": Attr((str, type(None)), max_length=200),
            "description": Attr(str, required=True, max_length=1000),
        },
        check=_check_visual,
    ),
    # Folio 3.4, the visual suite.
    "diagram": NodeSpec(
        BLOCK,
        attrs={
            "language": Attr(str, DIAGRAM_LANGUAGES, required=True),
            "source": Attr(str, required=True, max_length=20_000),
            "caption": Attr((str, type(None)), max_length=300),
        },
    ),
    "chart": NodeSpec(
        BLOCK,
        attrs={
            "kind": Attr(str, CHART_KINDS, required=True),
            "title": Attr((str, type(None)), max_length=200),
            "data": Attr(list, required=True),
        },
        check=_check_chart,
    ),
    "timeline": NodeSpec(BLOCK, attrs={"items": Attr(list, required=True)}, check=_check_timeline),
    "formula": NodeSpec(BLOCK, attrs={"latex": Attr(str, required=True, max_length=5000)}),
    "comparison": NodeSpec(BLOCK, ("comparisonSide",), min_children=2, max_children=3),
    "comparisonSide": NodeSpec(
        "side", (BLOCK,), {"title": Attr((str, type(None)), max_length=200)}, min_children=1
    ),
    "pageList": NodeSpec(
        BLOCK,
        attrs={
            "label": Attr(str, required=True, max_length=50),
            "limit": Attr(int, minimum=1, maximum=50),
            "space": Attr((str, type(None)), max_length=40),
        },
    ),
    # A database's view inside a page (Folio 3.6); the reader without access to the
    # database sees a placeholder, not its rows.
    "databaseView": NodeSpec(
        BLOCK,
        attrs={
            "database": Attr(str, required=True, max_length=36),
            "view": Attr((str, type(None)), max_length=40),
        },
        check=_check_database_view,
    ),
    # A pasted link (Folio 3.7): a card, or an iframe for the providers that embed. The
    # title is kept so the text and the RAG index read something better than a URL.
    "embed": NodeSpec(
        BLOCK,
        attrs={
            "url": Attr(str, required=True),
            "title": Attr((str, type(None)), max_length=300),
            "provider": Attr(
                (str, type(None)), ("youtube", "figma", "loom", "google_docs", "github", None)
            ),
        },
        check=_check_embed,
    ),
    "text": NodeSpec(INLINE),
    "hardBreak": NodeSpec(INLINE),
    "mention": NodeSpec(INLINE, attrs={"handle": Attr(str, required=True, max_length=64)}),
    "status": NodeSpec(
        INLINE,
        attrs={
            "text": Attr(str, required=True, max_length=40),
            "color": Attr(str, STATUS_COLORS),
        },
    ),
}
NODES["tableHeader"] = NODES["tableCell"]

MARKS: dict[str, dict[str, Attr]] = {
    "bold": {},
    "italic": {},
    "strike": {},
    "underline": {},
    "code": {},
    "link": {
        "href": Attr(str, required=True),
        "target": _OPT_STR,
        "rel": _OPT_STR,
        "class": _OPT_STR,
    },
}
LINK_SCHEMES = ("http://", "https://", "mailto:", "/", "#")


class SchemaError(ValidationFailed):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(
            f"Invalid document at {path}: {message}",
            code="invalid_document",
            errors=[{"field": path, "message": message}],
        )


@dataclass
class _Counter:
    nodes: int = 0


def _check_attrs(path: str, attrs: Any, spec: dict[str, Attr]) -> None:
    if attrs is None:
        attrs = {}
    if not isinstance(attrs, dict):
        raise SchemaError(f"{path}.attrs", "attrs must be an object")
    for name, value in attrs.items():
        rule = spec.get(name)
        if rule is None:
            raise SchemaError(f"{path}.attrs.{name}", "unknown attribute")
        if value is None and not rule.required:
            continue
        if isinstance(value, bool) and rule.kind is int:
            raise SchemaError(f"{path}.attrs.{name}", "must be a number")
        if not isinstance(value, rule.kind):
            raise SchemaError(f"{path}.attrs.{name}", "has the wrong type")
        if rule.choices and value not in rule.choices:
            valid = ", ".join(str(c) for c in rule.choices)
            raise SchemaError(f"{path}.attrs.{name}", f"must be one of {valid}")
        if isinstance(value, int) and not isinstance(value, bool):
            if rule.minimum is not None and value < rule.minimum:
                raise SchemaError(f"{path}.attrs.{name}", f"must be at least {rule.minimum}")
            if rule.maximum is not None and value > rule.maximum:
                raise SchemaError(f"{path}.attrs.{name}", f"must be at most {rule.maximum}")
        if isinstance(value, str) and len(value) > rule.max_length:
            raise SchemaError(f"{path}.attrs.{name}", f"is longer than {rule.max_length}")
    for name, rule in spec.items():
        if rule.required and attrs.get(name) is None:
            raise SchemaError(f"{path}.attrs.{name}", "is required")


def _check_marks(path: str, marks: Any) -> None:
    if not isinstance(marks, list):
        raise SchemaError(f"{path}.marks", "marks must be a list")
    for i, mark in enumerate(marks):
        here = f"{path}.marks[{i}]"
        if not isinstance(mark, dict) or mark.get("type") not in MARKS:
            raise SchemaError(here, "unknown mark")
        _check_attrs(here, mark.get("attrs"), MARKS[mark["type"]])
        if mark["type"] == "link" and not str(mark["attrs"]["href"]).startswith(LINK_SCHEMES):
            raise SchemaError(f"{here}.attrs.href", "links must be http(s), mailto or relative")


def _fits(child_type: str, allowed: tuple[str, ...]) -> bool:
    spec = NODES[child_type]
    return child_type in allowed or spec.group in allowed


def _check_node(node: Any, path: str, depth: int, counter: _Counter) -> None:
    counter.nodes += 1
    if counter.nodes > MAX_NODES:
        raise SchemaError(path, f"documents have at most {MAX_NODES} nodes")
    if depth > MAX_DEPTH:
        raise SchemaError(path, f"nesting deeper than {MAX_DEPTH}")
    if not isinstance(node, dict) or node.get("type") not in NODES:
        raise SchemaError(
            path, f"unknown node type {node.get('type') if isinstance(node, dict) else node!r}"
        )
    kind = node["type"]
    spec = NODES[kind]
    extra = set(node) - {"type", "attrs", "content", "text", "marks"}
    if extra:
        raise SchemaError(path, f"unexpected keys: {', '.join(sorted(extra))}")
    _check_attrs(path, node.get("attrs"), spec.attrs)
    if spec.check is not None:
        spec.check(path, node.get("attrs") or {})
    if kind == "text":
        if not isinstance(node.get("text"), str) or node["text"] == "":
            raise SchemaError(path, "text nodes need non-empty text")
        if "marks" in node:
            _check_marks(path, node["marks"])
        return
    if "text" in node or "marks" in node:
        raise SchemaError(path, f"{kind} cannot have text or marks")
    children = node.get("content", [])
    if not isinstance(children, list):
        raise SchemaError(f"{path}.content", "content must be a list")
    if len(children) < spec.min_children:
        raise SchemaError(f"{path}.content", f"{kind} needs at least {spec.min_children} child")
    if spec.max_children is not None and len(children) > spec.max_children:
        raise SchemaError(f"{path}.content", f"{kind} has at most {spec.max_children} children")
    for i, child in enumerate(children):
        here = f"{path}.content[{i}]"
        child_type = child.get("type") if isinstance(child, dict) else None
        if spec.leaf_text:
            if child_type != "text" or "marks" in child:
                raise SchemaError(here, f"{kind} holds plain text only")
        elif child_type not in NODES or not _fits(child_type, spec.content):
            raise SchemaError(here, f"{child_type!r} cannot go inside {kind}")
        _check_node(child, here, depth + 1, counter)


def validate(doc: Any) -> dict[str, Any]:
    """The document if it follows the schema; SchemaError (422) with the path otherwise."""
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        raise SchemaError("$", 'a document is {"type": "doc", "content": [...]}')
    if set(doc) - {"type", "content"}:
        raise SchemaError("$", "a document has only type and content")
    content = doc.get("content", [])
    if not isinstance(content, list):
        raise SchemaError("$.content", "content must be a list")
    counter = _Counter()
    for i, block in enumerate(content):
        here = f"$.content[{i}]"
        block_type = block.get("type") if isinstance(block, dict) else None
        if block_type not in NODES or NODES[block_type].group != BLOCK:
            raise SchemaError(here, f"{block_type!r} is not a block")
        _check_node(block, here, 1, counter)
    return doc


def empty() -> dict[str, Any]:
    return {"type": "doc", "content": []}
