"""Folio documents as Yjs (Folio 2.2, ADR 0039): TipTap JSON in and out of the
`XmlFragment("default")` that y-prosemirror edits in the browser.

Every node is an `XmlElement` named after its type, with its attributes; consecutive text
nodes share one `XmlText`, their marks stored as formatting attributes ({"bold": {}},
{"link": {"href": ...}}). Inline nodes that are not text (mentions, hard breaks, status)
are elements of their own, as y-prosemirror writes them.
"""

from typing import Any

import pycrdt

from radicle.folio.services import schema

FRAGMENT = "default"


def fragment(doc: pycrdt.Doc[Any]) -> pycrdt.XmlFragment:
    frag: pycrdt.XmlFragment = doc.get(FRAGMENT, type=pycrdt.XmlFragment)
    return frag


def _attrs(node: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in (node.get("attrs") or {}).items() if v is not None}


def _marks(node: dict[str, Any]) -> dict[str, Any] | None:
    marks = node.get("marks") or []
    return {m["type"]: dict(m.get("attrs") or {}) for m in marks} or None


def _fill(parent: Any, content: list[dict[str, Any]]) -> None:
    """Append the nodes to an XmlFragment or XmlElement (already in the document)."""
    text: Any = None
    for node in content:
        if node.get("type") == "text":
            if text is None:
                text = parent.children.append(pycrdt.XmlText())
            text.insert(len(text), node.get("text", ""), _marks(node))
            continue
        text = None
        element = parent.children.append(pycrdt.XmlElement(node["type"], _attrs(node)))
        _fill(element, node.get("content") or [])


def write(frag: pycrdt.XmlFragment, doc_json: dict[str, Any]) -> None:
    """Replace the fragment's content with the document, in one transaction."""
    with frag.doc.transaction():
        length = len(frag.children)
        if length:
            del frag.children[0:length]
        _fill(frag, doc_json.get("content") or [])


def append(frag: pycrdt.XmlFragment, blocks: list[dict[str, Any]]) -> None:
    """Add blocks at the end: concurrent edits elsewhere in the document stay."""
    with frag.doc.transaction():
        _fill(frag, blocks)


def _number(value: Any) -> Any:
    """Yjs numbers come back as floats; whole ones are ints in Folio's schema."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_number(v) for v in value]
    if isinstance(value, dict):
        return {k: _number(v) for k, v in value.items()}
    return value


def _text_nodes(text: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for chunk, formats in text.diff():
        if not isinstance(chunk, str) or not chunk:
            continue
        node: dict[str, Any] = {"type": "text", "text": chunk}
        if formats:
            node["marks"] = [
                {"type": name, "attrs": _number(attrs)} if attrs else {"type": name}
                for name, attrs in formats.items()
            ]
        out.append(node)
    return out


def _read(parent: Any) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for child in parent.children:
        if isinstance(child, pycrdt.XmlText):
            content.extend(_text_nodes(child))
            continue
        node: dict[str, Any] = {"type": child.tag}
        attrs = {k: _number(v) for k, v in child.attributes}
        if attrs:
            node["attrs"] = attrs
        children = _read(child)
        if children:
            node["content"] = children
        content.append(node)
    return content


def read(frag: pycrdt.XmlFragment) -> dict[str, Any]:
    """The fragment as TipTap JSON, cleaned to what Folio's schema accepts."""
    return clean({"type": "doc", "content": _read(frag)})


def _clean_marks(marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for mark in marks:
        spec = schema.MARKS.get(mark.get("type", ""))
        if spec is None:
            continue
        attrs = {k: v for k, v in (mark.get("attrs") or {}).items() if k in spec and v is not None}
        out.append({"type": mark["type"], "attrs": attrs} if attrs else {"type": mark["type"]})
    return out


def _clean(node: dict[str, Any]) -> dict[str, Any] | None:
    spec = schema.NODES.get(node.get("type", ""))
    if spec is None:
        return None
    out: dict[str, Any] = {"type": node["type"]}
    if node["type"] == "text":
        out["text"] = node.get("text", "")
        marks = _clean_marks(node.get("marks") or [])
        if marks:
            out["marks"] = marks
        return out
    attrs = {k: v for k, v in (node.get("attrs") or {}).items() if k in spec.attrs}
    attrs = {k: v for k, v in attrs.items() if v is not None}
    # A block still being set up (a whiteboard or database not picked yet) stays in the
    # room but out of the draft, as the editor does; otherwise nothing else would save.
    if not schema.attrs_valid(node["type"], attrs):
        return None
    if attrs:
        out["attrs"] = attrs
    children = [c for c in (_clean(c) for c in node.get("content") or []) if c is not None]
    if children:
        out["content"] = children
    return out


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    """Drop what the browser editor may add but Folio does not keep: unknown node types,
    marks and attributes, empty values, and blocks whose attributes aren't complete yet."""
    blocks = [c for c in (_clean(c) for c in doc.get("content") or []) if c is not None]
    return {"type": "doc", "content": blocks}


def from_json(doc_json: dict[str, Any]) -> pycrdt.Doc[Any]:
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    write(fragment(doc), doc_json)
    return doc


def to_json(doc: pycrdt.Doc[Any]) -> dict[str, Any]:
    return read(fragment(doc))
