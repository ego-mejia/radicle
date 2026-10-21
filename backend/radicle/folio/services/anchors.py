"""Where an inline comment points (Folio 2.3, ADR 0040).

An anchor is the quoted text plus a little context on each side, in the page's plain text
(`convert.to_text`). After every edit the anchor is found again:

1. the context on both sides, in order: the anchored text is whatever is between them now,
   so edits inside the quote keep the comment (the quote becomes the edited text);
2. else the quote itself, nearest to its old place: edits that touched the context;
3. else, or if nothing is left between the context, the comment is orphaned.

`yjs` is reserved for Yjs relative positions once the editor is collaborative (2.2).
"""

from dataclasses import dataclass
from typing import Any

CONTEXT = 32
MAX_QUOTE = 1000


@dataclass(frozen=True)
class Anchor:
    quote: str
    prefix: str
    suffix: str
    offset: int  # where the quote started, to break ties between repeats

    def as_json(self) -> dict[str, Any]:
        return {
            "quote": self.quote,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "offset": self.offset,
            "yjs": None,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> "Anchor":
        return Anchor(
            quote=str(data.get("quote", "")),
            prefix=str(data.get("prefix", "")),
            suffix=str(data.get("suffix", "")),
            offset=int(data.get("offset", 0) or 0),
        )


def at(text: str, start: int, end: int) -> Anchor:
    """The anchor for text[start:end]."""
    return Anchor(
        quote=text[start:end],
        prefix=text[max(0, start - CONTEXT) : start],
        suffix=text[end : end + CONTEXT],
        offset=start,
    )


def first(text: str, quote: str) -> Anchor | None:
    """The anchor for the first occurrence of `quote`, or None."""
    start = text.find(quote) if quote else -1
    return None if start < 0 else at(text, start, start + len(quote))


def _occurrences(text: str, needle: str) -> list[int]:
    found: list[int] = []
    start = text.find(needle) if needle else -1
    while start >= 0:
        found.append(start)
        start = text.find(needle, start + 1)
    return found


def _sides(context: str, *, from_end: bool) -> list[str]:
    """The context, then shorter slices of it next to the quote, for edits that touched
    its far end."""
    sizes = [len(context)] + [n for n in (16, 8) if n < len(context)]
    return [context[-n:] if from_end else context[:n] for n in sizes]


def _between(text: str, prefix: str, suffix: str, offset: int) -> tuple[int, int] | None:
    best: tuple[int, int] | None = None
    for p in _occurrences(text, prefix):
        start = p + len(prefix)
        end = text.find(suffix, start)
        if end < 0 or end - start > MAX_QUOTE:
            continue
        if best is None or abs(start - offset) < abs(best[0] - offset):
            best = (start, end)
    return best


def _between_context(text: str, anchor: Anchor) -> tuple[int, int] | None:
    if not anchor.prefix or not anchor.suffix:
        return None
    for prefix in _sides(anchor.prefix, from_end=True):
        for suffix in _sides(anchor.suffix, from_end=False):
            found = _between(text, prefix, suffix, anchor.offset)
            if found is not None:
                return found
    return None


def relocate(text: str, anchor: Anchor) -> Anchor | None:
    """The anchor in the new text, or None when its text is gone (orphaned)."""
    span = _between_context(text, anchor)
    if span is not None:
        start, end = span
        return at(text, start, end) if text[start:end].strip() else None
    starts = _occurrences(text, anchor.quote)
    if not starts:
        return None
    start = min(starts, key=lambda s: abs(s - anchor.offset))
    return at(text, start, start + len(anchor.quote))
