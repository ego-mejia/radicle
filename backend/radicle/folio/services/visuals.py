"""Visuals and the visual suite for agents (Folio 3.3 and 3.4): checking a visual before it
goes in a page, and adding a block to a draft under one of its headings.

A visual runs in a sandboxed iframe with no network and no access to the page; the checks
here tell an agent beforehand what the sandbox would block, so the visual works the first
time. The page gives it the Radicle tokens as CSS variables (`TOKENS`), in light or dark.
"""

import copy
import re
from dataclasses import dataclass, field
from typing import Any

from radicle.folio.services import chunking, convert, schema
from radicle.platform.errors import ValidationFailed

# CSS variables the page gives the iframe, in the reader's theme (docs/folio/fase-3.md):
# the colors, the fonts and the radius. The web app fills them from
# `frontend/src/styles/theme.ts` and sends new values when the theme changes.
TOKENS = (
    "--rdc-bg",
    "--rdc-surface",
    "--rdc-text",
    "--rdc-muted",
    "--rdc-accent",
    "--rdc-accent-fill",
    "--rdc-on-accent",
    "--rdc-border",
    "--rdc-danger",
    "--rdc-warning",
    "--rdc-info",
    "--rdc-font",
    "--rdc-mono",
    "--rdc-radius",
)

# The policy the page puts in every visual (the web app's VisualFrame sends the same).
CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:"
)
MAX_HEIGHT = 2000  # px; the iframe follows the visual's height up to this

_NETWORK = (
    (r"\bfetch\s*\(", "fetch()"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest"),
    (r"\bWebSocket\b", "WebSocket"),
    (r"\bEventSource\b", "EventSource"),
    (r"\bsendBeacon\b", "navigator.sendBeacon"),
    (r"\bimport\s*\(", "import()"),
    (r"@import\b", "CSS @import"),
)
_PAGE = re.compile(r"\b(?:parent|top|opener)\s*\.|\bwindow\.(?:parent|top|opener)\b")
_EXTERNAL = re.compile(
    r"""(?:\b(?:src|href|xlink:href|action|poster|data)\s*=\s*["']?|url\(\s*["']?)"""
    r"""((?:https?:)?//[^"')\s>]+)""",
    re.IGNORECASE,
)
_CSP_META = re.compile(r"<meta[^>]+http-equiv", re.IGNORECASE)
_TOKEN = re.compile(r"var\(\s*(--rdc-[a-z0-9-]+)")
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


@dataclass
class Report:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.problems


def check(fmt: str, code: str, description: str | None, title: str | None = "untitled") -> Report:
    """What would stop the visual (problems) and what would make it better (warnings)."""
    out = Report()
    if fmt not in schema.VISUAL_FORMATS:
        out.problems.append(f"format is svg or html, not {fmt!r}.")
    if not code.strip():
        out.problems.append("code is empty: send the SVG or HTML to show.")
    size = len(code.encode())
    if size > schema.MAX_VISUAL:
        out.problems.append(
            f"code is {size // 1024} KB; the limit is {schema.MAX_VISUAL // 1024} KB. "
            "Simplify it or split it in two visuals."
        )
    if fmt == "svg" and code.strip() and not re.match(r"\s*(<\?xml[^>]*>\s*)?<svg\b", code):
        out.problems.append("An svg visual starts with <svg>; use format html for anything else.")
    if not (description or "").strip():
        out.problems.append(
            "description is required: say what the visual shows. It is the alt text and "
            "what search reads."
        )
    elif len(description or "") < 20:
        out.warnings.append("The description is short; say what someone should learn from it.")
    if not (title or "").strip():
        out.problems.append("title is required to publish: name the visual in a few words.")
    for pattern, name in _NETWORK:
        if re.search(pattern, code):
            out.problems.append(
                f"{name} needs the network, which the sandbox blocks. Put the data in the code."
            )
    for url in sorted(set(_EXTERNAL.findall(code))):
        out.problems.append(
            f"{url} is outside the visual and won't load. Inline it (images as data: URLs)."
        )
    if _PAGE.search(code):
        out.problems.append(
            "The visual can't reach the page around it (parent, top, opener); keep it "
            "self-contained."
        )
    if _CSP_META.search(code):
        out.problems.append("Remove the <meta http-equiv>: the page sets the visual's policy.")
    used = set(_TOKEN.findall(code))
    for token in sorted(used - set(TOKENS)):
        out.problems.append(f"{token} is not a Radicle token. Valid: {', '.join(TOKENS)}.")
    if not used:
        out.warnings.append(
            "It uses no Radicle tokens, so it won't follow light and dark mode. Use "
            "var(--rdc-text), var(--rdc-accent) and the others "
            "(folio://guide/visuals)."
        )
    elif _HEX.search(code):
        out.warnings.append("Some colors are fixed (#hex); prefer the tokens so dark mode works.")
    return out


def require_valid(
    fmt: str, code: str, description: str | None, title: str | None = "untitled"
) -> Report:
    report = check(fmt, code, description, title)
    if not report.valid:
        raise ValidationFailed(
            "The visual can't go in as it is: " + " ".join(report.problems),
            errors=[{"field": "code", "message": p} for p in report.problems],
        )
    return report


def _heading_text(node: dict[str, Any]) -> str:
    return convert.inline(node.get("content", [])).replace("\\", "").strip()


def _matches(text: str, wanted: str) -> bool:
    slug = chunking.anchor_for
    return text.lower() == wanted.lower() or slug(text, set()) == slug(wanted, set())


def insert(
    doc: dict[str, Any], block: dict[str, Any], after_heading: str | None = None
) -> dict[str, Any]:
    """The document with the block at the end of the section under `after_heading` (before
    the next heading of the same or a higher level), or at the end of the document."""
    content = list(doc.get("content", []))
    at = len(content)
    if after_heading:
        wanted = after_heading.strip().lstrip("#").strip()
        found = next(
            (
                i
                for i, n in enumerate(content)
                if n.get("type") == "heading" and _matches(_heading_text(n), wanted)
            ),
            None,
        )
        if found is None:
            headings = [_heading_text(n) for n in content if n.get("type") == "heading"]
            raise ValidationFailed(
                f"There is no heading '{wanted}' in the draft. "
                + (
                    f"Headings: {', '.join(headings)}."
                    if headings
                    else "It has no headings; leave after_heading out to add it at the end."
                ),
                errors=[{"field": "after_heading", "message": "not found"}],
            )
        level = content[found]["attrs"]["level"]
        at = next(
            (
                i
                for i in range(found + 1, len(content))
                if content[i].get("type") == "heading" and content[i]["attrs"]["level"] <= level
            ),
            len(content),
        )
    if block.get("type") == "visual":
        attrs = block.get("attrs") or {}
        fields = ("format", "code", "description", "title")
        require_valid(*(attrs.get(k) or "" for k in fields))
    return schema.validate({"type": "doc", "content": [*content[:at], block, *content[at:]]})


def _visuals(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found = []
    for n in nodes:
        if n.get("type") == "visual":
            found.append(n)
        found += _visuals(n.get("content") or [])
    return found


def require_publishable(doc: dict[str, Any]) -> None:
    """A draft goes out only when every visual has a title; the schema already asks every
    visual for its description."""
    visuals = _visuals(doc.get("content") or [])
    untitled = [i + 1 for i, v in enumerate(visuals) if not (v.get("attrs") or {}).get("title")]
    if untitled:
        which = ", ".join(str(n) for n in untitled)
        raise ValidationFailed(
            f"Give every visual a title before publishing (visual {which} has none).",
            errors=[{"field": "content", "message": f"visual {n} needs a title"} for n in untitled],
        )


# Editing the visuals already in a draft (ADR 0046): an agent lists them, reads one and
# changes or removes it by its position in the document, without rewriting the page.
VISUAL_FIELDS = ("format", "code", "title", "description")


def _paths(nodes: list[dict[str, Any]], at: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
    """Where each visual is, in document order, as indexes into nested `content` lists."""
    found: list[tuple[int, ...]] = []
    for i, n in enumerate(nodes):
        here = (*at, i)
        if n.get("type") == "visual":
            found.append(here)
        found += _paths(n.get("content") or [], here)
    return found


def _locate(doc: dict[str, Any], index: int) -> tuple[list[dict[str, Any]], int]:
    """The list that holds visual `index` and its position there."""
    paths = _paths(doc.get("content") or [])
    if not 0 <= index < len(paths):
        count = len(paths)
        hint = (
            f"valid indexes are 0 to {count - 1}" if count else "add one with insert_visual first"
        )
        raise ValidationFailed(
            f"There is no visual {index}: the draft has {count} visual(s); {hint}.",
            errors=[{"field": "index", "message": "out of range"}],
        )
    *parents, last = paths[index]
    holder: list[dict[str, Any]] = doc["content"]
    for i in parents:
        holder = holder[i]["content"]
    return holder, last


def summary(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every visual of the document, in order: index, title, format, description, size."""
    out = []
    for i, v in enumerate(_visuals(doc.get("content") or [])):
        attrs = v.get("attrs") or {}
        out.append(
            {
                "index": i,
                "title": attrs.get("title"),
                "format": attrs.get("format"),
                "description": attrs.get("description"),
                "size": len((attrs.get("code") or "").encode()),
            }
        )
    return out


def get_visual(doc: dict[str, Any], index: int) -> dict[str, Any]:
    holder, at = _locate(doc, index)
    attrs = holder[at].get("attrs") or {}
    return {"index": index} | {k: attrs.get(k) for k in VISUAL_FIELDS}


def update_visual(doc: dict[str, Any], index: int, changes: dict[str, Any]) -> dict[str, Any]:
    """The document with visual `index` changed (only the given fields), checked again."""
    edited = copy.deepcopy(doc)
    holder, at = _locate(edited, index)
    attrs = {**(holder[at].get("attrs") or {})}
    attrs.update({k: v for k, v in changes.items() if k in VISUAL_FIELDS and v is not None})
    require_valid(*(attrs.get(k) or "" for k in ("format", "code", "description", "title")))
    holder[at] = {**holder[at], "attrs": attrs}
    return schema.validate(edited)


def remove_visual(doc: dict[str, Any], index: int) -> dict[str, Any]:
    edited = copy.deepcopy(doc)
    holder, at = _locate(edited, index)
    del holder[at]
    return schema.validate(edited)
