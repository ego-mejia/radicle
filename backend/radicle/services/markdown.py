"""Checklist and @mention parsing over markdown, ignoring code."""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_ITEM_RE = re.compile(r"^(?P<prefix>\s*[-*]\s+\[)(?P<mark>[ xX])(?P<suffix>\]\s+)(?P<text>.*)$")
_INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
# A mention is @handle not glued to a preceding word char, dot or @ (so emails don't count).
_MENTION_RE = re.compile(r"(?<![\w.@/])@([A-Za-z0-9][A-Za-z0-9_-]{1,31})(?![\w@-])")


@dataclass(frozen=True)
class ChecklistItem:
    index: int
    line: int
    text: str
    checked: bool
    assignee: str | None


def _prose_lines(markdown: str) -> Iterator[tuple[int, str]]:
    """Yield (line number, line) for lines outside fenced code blocks."""
    fence: str | None = None
    for number, line in enumerate(markdown.split("\n")):
        match = _FENCE_RE.match(line)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        yield number, line


def _without_inline_code(line: str) -> str:
    return _INLINE_CODE_RE.sub(" ", line)


def mentions_in_line(line: str) -> list[str]:
    return [m.lower() for m in _MENTION_RE.findall(_without_inline_code(line))]


def parse_checklist(markdown: str) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    for number, line in _prose_lines(markdown):
        match = _ITEM_RE.match(line)
        if not match:
            continue
        text = match.group("text").rstrip()
        handles = mentions_in_line(text)
        assignee = handles[-1] if handles else None
        if assignee is not None:
            # Drop the trailing "@handle" from the display text when it ends the line.
            text = re.sub(rf"\s*@{re.escape(assignee)}\s*$", "", text, flags=re.IGNORECASE)
        items.append(
            ChecklistItem(
                index=len(items),
                line=number,
                text=text.strip(),
                checked=match.group("mark") in "xX",
                assignee=assignee,
            )
        )
    return items


def set_checklist_item(markdown: str, index: int, checked: bool) -> tuple[str, ChecklistItem]:
    """Rewrite only the line of item `index`. Raises IndexError if there is no such item."""
    items = parse_checklist(markdown)
    if not 0 <= index < len(items):
        raise IndexError(index)
    item = items[index]
    lines = markdown.split("\n")
    match = _ITEM_RE.match(lines[item.line])
    if match is None:  # pragma: no cover - parse_checklist already matched this line
        raise IndexError(index)
    mark = "x" if checked else " "
    lines[item.line] = f"{match.group('prefix')}{mark}{match.group('suffix')}{match.group('text')}"
    return "\n".join(lines), item


def extract_mentions(markdown: str) -> list[str]:
    """Unique lowercase handles mentioned outside code, in order of first appearance."""
    seen: dict[str, None] = {}
    for _, line in _prose_lines(markdown):
        for handle in mentions_in_line(line):
            seen.setdefault(handle, None)
    return list(seen)
