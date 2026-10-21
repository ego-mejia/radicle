"""Chunking (Folio 1.6): a published version cut into sections for search and the RAG
index. One chunk per heading and its content; long sections are split in 300 to 500
tokens with about 50 of overlap, never through a table, a code block or a list. Each chunk
keeps its heading path and the anchor of its heading, so an answer can cite the section.
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from radicle.folio.services import convert

Node = dict[str, Any]
MAX_TOKENS = 500
TARGET_TOKENS = 450
OVERLAP_TOKENS = 50
# The same sizes in words (tokens ~ 4/3 of words).
TARGET_WORDS = TARGET_TOKENS * 3 // 4
OVERLAP_WORDS = OVERLAP_TOKENS * 3 // 4
ATOMIC = {"table", "codeBlock", "bulletList", "orderedList", "taskList"}


def tokens(text: str) -> int:
    """A cheap estimate (about 4 tokens per 3 words), good enough to size chunks."""
    return math.ceil(len(text.split()) * 4 / 3)


def anchor_for(text: str, taken: set[str]) -> str:
    base = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "section"
    anchor, n = base, 1
    while anchor in taken:
        n += 1
        anchor = f"{base}-{n}"
    taken.add(anchor)
    return anchor


def _heading_text(node: Node) -> str:
    return convert.inline(node.get("content", [])).replace("\\", "")


def _block_text(node: Node) -> str:
    """Markdown for tables and code (structure matters), captions for media."""
    attrs = node.get("attrs") or {}
    if node["type"] == "image":
        return " ".join(v for v in (attrs.get("alt"), attrs.get("caption")) if v)
    if node["type"] in ("file", "video"):
        return str(attrs.get("name") or attrs.get("caption") or "")
    if node["type"] in ("tableOfContents", "childPages", "horizontalRule"):
        return ""
    return convert.block(node)


@dataclass
class Chunk:
    position: int
    heading_path: list[str]
    anchor: str | None
    text: str
    token_count: int = 0


@dataclass
class _Section:
    path: list[str]
    anchor: str | None
    blocks: list[Node] = field(default_factory=list)


def _sections(doc: Node) -> list[_Section]:
    taken: set[str] = set()
    stack: list[tuple[int, str]] = []
    sections = [_Section([], None)]
    for node in doc.get("content", []):
        if node["type"] == "heading":
            level = int((node.get("attrs") or {}).get("level", 1))
            title = _heading_text(node)
            stack = [s for s in stack if s[0] < level] + [(level, title)]
            sections.append(_Section([t for _, t in stack], anchor_for(title, taken)))
        else:
            sections[-1].blocks.append(node)
    return [s for s in sections if s.blocks or s.anchor]


def _windows(text: str) -> list[str]:
    """A paragraph longer than a chunk, cut by words into overlapping windows."""
    words = text.split()
    size, step = TARGET_WORDS, TARGET_WORDS - OVERLAP_WORDS
    return [
        " ".join(words[i : i + size]) for i in range(0, max(len(words) - OVERLAP_WORDS, 1), step)
    ]


def _split(texts: list[tuple[str, bool]]) -> list[str]:
    """Group block texts into pieces of up to TARGET_TOKENS. The next piece starts with
    the last words of the previous one, unless that block is a table, code or a list."""
    units: list[tuple[str, bool]] = []
    for text, atomic in texts:
        if not atomic and tokens(text) > TARGET_TOKENS:
            units += [(w, False) for w in _windows(text)]
        else:
            units.append((text, atomic))
    pieces: list[str] = []
    current: list[tuple[str, bool]] = []
    size = 0
    for text, atomic in units:
        cost = tokens(text)
        if current and size + cost > TARGET_TOKENS:
            pieces.append("\n\n".join(t for t, _ in current))
            last, last_atomic = current[-1]
            current, size = [], 0
            if not last_atomic:
                tail = " ".join(last.split()[-OVERLAP_WORDS:])
                current, size = [(tail, False)], tokens(tail)
        current.append((text, atomic))
        size += cost
    if current:
        pieces.append("\n\n".join(t for t, _ in current))
    return pieces


def chunk(doc: Node) -> list[Chunk]:
    """The document's chunks in reading order."""
    out: list[Chunk] = []
    for section in _sections(doc):
        texts = [(_block_text(b), b["type"] in ATOMIC) for b in section.blocks]
        texts = [(t, a) for t, a in texts if t.strip()]
        body = "\n\n".join(t for t, _ in texts)
        pieces = [body] if tokens(body) <= MAX_TOKENS else _split(texts)
        for piece in pieces:
            if not piece.strip() and not section.path:
                continue
            out.append(Chunk(len(out), section.path, section.anchor, piece, tokens(piece)))
    return out


def embedding_input(title: str, description: str, c: Chunk) -> str:
    """What gets embedded: the document's title and description, then where the section
    sits and its text."""
    where = " > ".join(c.heading_path)
    return "\n".join(part for part in (title, description, where, c.text) if part)
