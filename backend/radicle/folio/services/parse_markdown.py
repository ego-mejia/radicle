"""Markdown to Folio documents (Folio 1.2); `convert.to_markdown` goes the other way. The
syntax is in docs/folio/markdown.md. Directives are resolved line by line first (never in
fenced code); the rest goes through markdown-it (CommonMark, GFM tables and strike, no HTML).
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from radicle.folio.services import schema

Node = dict[str, Any]

_md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])

_OPEN = re.compile(r"^(:{3,})(panel|expand|columns|column|compare|side)(\{.*\})?\s*$")
_CLOSE = re.compile(r"^:{3,}\s*$")
_LEAF = re.compile(
    r"^::(file|video|pages|database|whiteboard|calendar|embed|tickets|progress)(\{.*\})\s*$"
)
_INFO = re.compile(r"^(?P<name>[\w-]+)\s*(?P<attrs>\{.*\})?\s*$")
_ACTION = re.compile(r"^::task\[(?P<label>.*)\](?P<attrs>\{[^}]*\})?\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_ATTR = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|[^\s}]+)')
_INLINE = re.compile(
    r":status\[(?P<status>[^\]]*)\](?P<status_attrs>\{[^}]*\})?"
    r"|(?<![\w@.])@(?P<handle>[a-z0-9][a-z0-9_-]{0,63})"
    r"|:ticket\[(?P<ticket>[A-Za-z][A-Za-z0-9]{1,9}-\d{1,9})\]"
)
_TASK = re.compile(r"^\[( |x|X)\] ")
_BOX = re.compile(r"^\[([ x~])\]\s*")


def _attrs(text: str | None) -> dict[str, str]:
    if not text:
        return {}
    out = {}
    for key, value in _ATTR.findall(text.strip("{}")):
        if value.startswith('"'):
            value = re.sub(r"\\(.)", r"\1", value[1:-1])
        out[key] = value
    return out


@dataclass
class _Container:
    name: str
    attrs: dict[str, str]
    items: list[Any] = field(default_factory=list)


def _segments(markdown: str) -> list[Any]:
    """Lines grouped into Markdown text, directive containers and leaf directives."""
    root = _Container("doc", {})
    stack = [root]
    buffer: list[str] = []
    fence: str | None = None

    def flush() -> None:
        if buffer:
            stack[-1].items.append("\n".join(buffer))
            buffer.clear()

    for line in markdown.replace("\r\n", "\n").split("\n"):
        mark = _FENCE.match(line)
        if fence is not None:
            buffer.append(line)
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence):
                fence = None
            continue
        if mark:
            fence = mark.group(1)
            buffer.append(line)
            continue
        stripped = line.strip()
        if (opened := _OPEN.match(stripped)) is not None:
            flush()
            container = _Container(opened.group(2), _attrs(opened.group(3)))
            stack[-1].items.append(container)
            stack.append(container)
        elif _CLOSE.match(stripped) and len(stack) > 1:
            flush()
            stack.pop()
        elif (leaf := _LEAF.match(stripped)) is not None:
            flush()
            stack[-1].items.append((leaf.group(1), _attrs(leaf.group(2))))
        elif (action := _ACTION.match(stripped)) is not None:
            flush()
            attrs = _attrs(action.group("attrs")) | {"__label": action.group("label")}
            stack[-1].items.append(("task", attrs))
        elif stripped in ("[[toc]]", "[[children]]"):
            flush()
            stack[-1].items.append(("toc" if stripped == "[[toc]]" else "children", {}))
        else:
            buffer.append(line)
    flush()
    return root.items


# --- inline ---------------------------------------------------------------------------------


def _text(text: str, marks: list[Node]) -> list[Node]:
    """Plain text with mentions and inline status pulled out."""
    out: list[Node] = []
    pos = 0
    in_code = any(m["type"] == "code" for m in marks)
    for match in [] if in_code else _INLINE.finditer(text):
        if match.start() > pos:
            out.append(_textnode(text[pos : match.start()], marks))
        if match.group("handle"):
            out.append({"type": "mention", "attrs": {"handle": match.group("handle")}})
        elif match.group("ticket"):
            out.append({"type": "ticket", "attrs": {"key": match.group("ticket").upper()}})
        else:
            attrs: dict[str, Any] = {"text": match.group("status") or "status"}
            color = _attrs(match.group("status_attrs")).get("color")
            if color in schema.STATUS_COLORS:
                attrs["color"] = color
            out.append({"type": "status", "attrs": attrs})
        pos = match.end()
    if pos < len(text):
        out.append(_textnode(text[pos:], marks))
    return [n for n in out if n["type"] != "text" or n["text"]]


def _textnode(text: str, marks: list[Node]) -> Node:
    node: Node = {"type": "text", "text": text}
    if marks:
        node["marks"] = [dict(m) for m in marks]
    return node


_ORDER = ("bold", "italic", "strike", "underline", "code", "link")


def _sorted_marks(marks: list[Node]) -> list[Node]:
    return sorted(marks, key=lambda m: _ORDER.index(m["type"]))


def _inline_math(out: list[Node], tokens: list[Token], i: int) -> bool:
    """$`latex`$ (as GitLab writes inline math): a code span between two dollar signs.
    Takes the opening $ off the text before; the caller drops the closing one."""
    before = out[-1] if out else None
    after = tokens[i + 1] if i + 1 < len(tokens) else None
    if not (before and before["type"] == "text" and before["text"].endswith("$")):
        return False
    if after is None or after.type != "text" or not after.content.startswith("$"):
        return False
    before["text"] = before["text"][:-1]
    return True


def _inline(tokens: list[Token]) -> list[Node]:
    out: list[Node] = []
    marks: list[Node] = []
    underline = 0
    pairs = {"strong": "bold", "em": "italic", "s": "strike"}
    closing: set[int] = set()  # text tokens that start with the $ closing inline math

    def current() -> list[Node]:
        extra = [{"type": "underline"}] if underline else []
        return _sorted_marks(marks + extra)

    for i, tok in enumerate(tokens):
        kind = tok.type
        if kind == "text":
            text = tok.content
            if i in closing:
                text = text[1:]
            # :u[...] may span several tokens (:u[**x**]); track the brackets.
            while text:
                if ":u[" in text:
                    before, _, text = text.partition(":u[")
                    out += _text(before, current())
                    underline += 1
                    continue
                if underline and "]" in text:
                    before, _, text = text.partition("]")
                    out += _text(before, current())
                    underline -= 1
                    continue
                out += _text(text, current())
                text = ""
        elif kind == "code_inline" and _inline_math(out, tokens, i):
            out[-1:] = [n for n in out[-1:] if n.get("text") != ""]
            closing.add(i + 1)
            out.append({"type": "inlineFormula", "attrs": {"latex": tok.content}})
        elif kind == "code_inline":
            out.append(_textnode(tok.content, _sorted_marks([*current(), {"type": "code"}])))
        elif kind in ("softbreak",):
            out += _text(" ", current())
        elif kind == "hardbreak":
            out.append({"type": "hardBreak"})
        elif kind.endswith("_open") and kind[:-5] in pairs:
            marks.append({"type": pairs[kind[:-5]]})
        elif kind.endswith("_close") and kind[:-6] in pairs:
            name = pairs[kind[:-6]]
            marks = [m for m in marks if m["type"] != name]
        elif kind == "link_open":
            marks.append({"type": "link", "attrs": {"href": str(tok.attrs.get("href", ""))}})
        elif kind == "link_close":
            marks = [m for m in marks if m["type"] != "link"]
    return _merge(out)


def _merge(nodes: list[Node]) -> list[Node]:
    out: list[Node] = []
    for node in nodes:
        last = out[-1] if out else None
        if (
            last is not None
            and node["type"] == last["type"] == "text"
            and node.get("marks") == last.get("marks")
        ):
            last["text"] += node["text"]
        else:
            out.append(node)
    return out


# --- blocks ---------------------------------------------------------------------------------


def _image(inline_tokens: list[Token]) -> Node | None:
    """A paragraph that is only an image (and its {size align}) is an image block."""
    parts = [t for t in inline_tokens if not (t.type == "text" and not t.content.strip())]
    if not parts or parts[0].type != "image":
        return None
    extra = parts[1:]
    if len(extra) > 1 or (extra and not re.fullmatch(r"\{.*\}", extra[0].content.strip())):
        return None
    tok = parts[0]
    src = str(tok.attrs.get("src", ""))
    attrs: dict[str, Any] = {}
    if src.startswith("asset:"):
        attrs["assetId"] = src[len("asset:") :]
    elif src:
        attrs["src"] = src
    alt = "".join(c.content for c in (tok.children or []))
    if alt:
        attrs["alt"] = alt
    if tok.attrs.get("title"):
        attrs["caption"] = str(tok.attrs["title"])
    options = _attrs(extra[0].content.strip()) if extra else {}
    if options.get("size") in schema.IMAGE_SIZES:
        attrs["size"] = options["size"]
    if options.get("align") in schema.ALIGNS:
        attrs["align"] = options["align"]
    return {"type": "image", "attrs": attrs}


def _paragraph(inline_tokens: list[Token]) -> Node:
    return _image(inline_tokens) or {"type": "paragraph", "content": _inline(inline_tokens)}


def _clean(node: Node) -> Node:
    if node.get("content") == []:
        del node["content"]
    return node


class _Blocks:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def until(self, closing: str | None) -> list[Node]:
        out: list[Node] = []
        while self.i < len(self.tokens):
            tok = self.tokens[self.i]
            if closing and tok.type == closing:
                self.i += 1
                return out
            node = self.one()
            if node is not None:
                out.append(node)
        return out

    def one(self) -> Node | None:
        tok = self.tokens[self.i]
        self.i += 1
        kind = tok.type
        if kind == "heading_open":
            level = min(int(tok.tag[1]), 4)
            content = _inline(self.tokens[self.i].children or [])
            self.i += 2
            return _clean({"type": "heading", "attrs": {"level": level}, "content": content})
        if kind == "paragraph_open":
            node = _paragraph(self.tokens[self.i].children or [])
            self.i += 2
            return _clean(node)
        if kind in ("bullet_list_open", "ordered_list_open"):
            return self.list(tok)
        if kind == "blockquote_open":
            return {"type": "blockquote", "content": self.until("blockquote_close") or [_empty()]}
        if kind in ("fence", "code_block"):
            code = tok.content[:-1] if tok.content.endswith("\n") else tok.content
            special = _fenced_block(tok.info.strip(), code) if kind == "fence" else None
            if special is not None:
                return special
            block: Node = {"type": "codeBlock", "attrs": {"language": tok.info.strip() or None}}
            if code:
                block["content"] = [{"type": "text", "text": code}]
            return block
        if kind == "hr":
            return {"type": "horizontalRule"}
        if kind == "table_open":
            return self.table()
        return None  # html is off; anything else carries no content

    def list(self, opening: Token) -> Node:
        ordered = opening.type == "ordered_list_open"
        closing = "ordered_list_close" if ordered else "bullet_list_close"
        items: list[Node] = []
        task = not ordered
        while self.tokens[self.i].type != closing:
            self.i += 1  # list_item_open
            content = self.until("list_item_close") or [_empty()]
            first = content[0]
            match = None
            if first["type"] == "paragraph" and first.get("content"):
                head = first["content"][0]
                if head["type"] == "text" and not head.get("marks"):
                    match = _TASK.match(head["text"])
            if match is None:
                task = False
            items.append({"content": content, "task": match})
        self.i += 1
        if task:
            return {"type": "taskList", "content": [_task(item) for item in items]}
        node: Node = {
            "type": "orderedList" if ordered else "bulletList",
            "content": [{"type": "listItem", "content": item["content"]} for item in items],
        }
        if ordered:
            node["attrs"] = {"start": int(opening.attrs.get("start", 1) or 1)}
        return node

    def table(self) -> Node:
        rows: list[Node] = []
        cell_type = "tableHeader"
        while self.tokens[self.i].type != "table_close":
            tok = self.tokens[self.i]
            self.i += 1
            if tok.type == "tbody_open":
                cell_type = "tableCell"
            elif tok.type == "tr_open":
                rows.append({"type": "tableRow", "content": []})
            elif tok.type in ("th_open", "td_open"):
                inline_tok = self.tokens[self.i]
                content = _inline(inline_tok.children or [])
                paragraph = _clean({"type": "paragraph", "content": content})
                rows[-1]["content"].append({"type": cell_type, "content": [paragraph]})
                self.i += 2
        self.i += 1
        return {"type": "table", "content": rows}


def _task(item: dict[str, Any]) -> Node:
    content = item["content"]
    first = content[0]
    head = first["content"][0]
    rest = head["text"][item["task"].end() :]
    first["content"] = ([{**head, "text": rest}] if rest else []) + first["content"][1:]
    _clean(first)
    checked = item["task"].group(1).lower() == "x"
    return {"type": "taskItem", "attrs": {"checked": checked}, "content": content}


def _empty() -> Node:
    return {"type": "paragraph"}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _number(text: str) -> float | int | None:
    try:
        value = float(text.replace(",", ""))
    except ValueError:
        return None
    return int(value) if value.is_integer() and "." not in text else value


def _chart(attrs: dict[str, str], body: str) -> Node | None:
    kind = attrs.get("kind") if attrs.get("kind") in schema.CHART_KINDS else "bar"
    if attrs.get("source") == "table":
        chart: Node = {"type": "chart", "attrs": {"kind": kind, "source": "table"}}
        if attrs.get("title"):
            chart["attrs"]["title"] = attrs["title"]
        return chart
    lines = [ln for ln in body.split("\n") if ln.strip() and not re.fullmatch(r"[\s|:-]+", ln)]
    if len(lines) < 2:
        return None
    header = _cells(lines[0])
    rows: list[list[Any]] = [header]
    for line in lines[1:]:
        cells = _cells(line)[: len(header)]
        cells += [""] * (len(header) - len(cells))
        values = [_number(c) for c in cells[1:]]
        rows.append([cells[0], *[v if v is not None else 0 for v in values]])
    chart = {"type": "chart", "attrs": {"kind": kind, "data": rows}}
    if attrs.get("title"):
        chart["attrs"]["title"] = attrs["title"]
    return chart


def _timeline(body: str) -> Node | None:
    items = []
    for line in body.split("\n"):
        if not line.strip():
            continue
        box = _BOX.match(line.strip())
        line = line.strip()[box.end() :] if box else line
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) == 1:
            parts = ["", parts[0]]
        item = {"date": parts[0], "title": parts[1], "text": parts[2] if len(parts) > 2 else ""}
        if box:
            item["status"] = {"x": "done", "~": "in_progress", " ": "planned"}[box.group(1)]
        items.append({k: v for k, v in item.items() if v})
    items = [i for i in items if i.get("title")]
    return {"type": "timeline", "attrs": {"items": items}} if items else None


def _fenced_block(info: str, body: str) -> Node | None:
    """Fences named mermaid, math, chart, timeline or visual are Folio blocks (3.3, 3.4);
    one that doesn't make a valid block stays a code block."""
    match = _INFO.match(info)
    if match is None:
        return None
    name, attrs = match.group("name").lower(), _attrs(match.group("attrs"))
    node: Node | None = None
    if name == "mermaid" and body.strip():
        node = {"type": "diagram", "attrs": {"language": "mermaid", "source": body}}
        if attrs.get("caption"):
            node["attrs"]["caption"] = attrs["caption"]
    elif name == "math" and body.strip():
        node = {"type": "formula", "attrs": {"latex": body}}
    elif name == "chart":
        node = _chart(attrs, body)
    elif name == "timeline":
        node = _timeline(body)
    elif name == "visual" and body.strip() and attrs.get("description"):
        fmt = attrs.get("format") if attrs.get("format") in schema.VISUAL_FORMATS else "svg"
        node = {
            "type": "visual",
            "attrs": {"format": fmt, "code": body, "description": attrs["description"]},
        }
        if attrs.get("title"):
            node["attrs"]["title"] = attrs["title"]
    if node is None:
        return None
    try:
        schema.validate({"type": "doc", "content": [node]})
    except schema.SchemaError:
        return None
    return node


def _action_item(attrs: dict[str, str]) -> Node:
    """`::task[text]{id=… assignee=ana due=2026-11-01 done=true}`; without an id, one is
    made up, so items written in Markdown by agents still get a stable one."""
    tokens = _md.parseInline(attrs.get("__label", ""))
    content = _merge(_inline(tokens[0].children or [])) if tokens else []
    due = attrs.get("due")
    try:
        due = date.fromisoformat(due).isoformat() if due else None
    except ValueError:
        due = None
    item_attrs: dict[str, Any] = {
        "id": (attrs.get("id") or f"ai-{uuid.uuid4().hex[:12]}")[:64],
        "done": attrs.get("done", "").lower() in ("true", "1", "yes", "x"),
        "assignee": (attrs.get("assignee") or "").lstrip("@").lower() or None,
        "due": due,
    }
    node: Node = {"type": "actionItem", "attrs": item_attrs}
    if content:
        node["content"] = content
    return node


def _markdown_blocks(text: str) -> list[Node]:
    return _Blocks(_md.parse(text)).until(None)


def _convert(items: list[Any], parent: str = "doc") -> list[Node]:
    out: list[Node] = []
    for item in items:
        if isinstance(item, str):
            out += _markdown_blocks(item)
        elif isinstance(item, tuple):
            name, attrs = item
            if name == "toc":
                out.append({"type": "tableOfContents"})
            elif name == "children":
                out.append({"type": "childPages"})
            elif name == "file" and attrs.get("asset"):
                file_attrs: dict[str, Any] = {"assetId": attrs["asset"]}
                if attrs.get("name"):
                    file_attrs["name"] = attrs["name"]
                if attrs.get("type"):
                    file_attrs["mimeType"] = attrs["type"]
                if (attrs.get("size") or "").isdigit():
                    file_attrs["size"] = int(attrs["size"])
                out.append({"type": "file", "attrs": file_attrs})
            elif name == "video":
                keys = (("src", "src"), ("assetId", "asset"), ("caption", "caption"))
                video = {k: attrs[v] for k, v in keys if attrs.get(v)}
                out.append({"type": "video", "attrs": video})
            elif name == "embed" and attrs.get("url", "").startswith(("https://", "http://")):
                embed: dict[str, Any] = {"url": attrs["url"]}
                if attrs.get("title"):
                    embed["title"] = attrs["title"]
                out.append({"type": "embed", "attrs": embed})
            elif name == "task":
                out.append(_action_item(attrs))
            elif name == "pages" and attrs.get("label"):
                page_list: dict[str, Any] = {"label": attrs["label"].lstrip("#").lower()[:50]}
                if (attrs.get("limit") or "").isdigit():
                    page_list["limit"] = min(max(int(attrs["limit"]), 1), 50)
                if attrs.get("space"):
                    page_list["space"] = attrs["space"]
                if attrs.get("order") in schema.PAGE_LIST_ORDERS:
                    page_list["order"] = attrs["order"]
                out.append({"type": "pageList", "attrs": page_list})
            elif name == "database" and attrs.get("id"):
                view: dict[str, Any] = {"database": attrs["id"]}
                if attrs.get("view"):
                    view["view"] = attrs["view"]
                out.append({"type": "databaseView", "attrs": view})
            elif name == "tickets" and attrs.get("rql"):
                table: dict[str, Any] = {"rql": attrs["rql"][:2000]}
                if attrs.get("title"):
                    table["title"] = attrs["title"][:200]
                if (attrs.get("limit") or "").isdigit():
                    table["limit"] = min(max(int(attrs["limit"]), 1), 100)
                out.append({"type": "ticketTable", "attrs": table})
            elif name == "progress":
                title = (attrs.get("title") or "")[:200]
                out.append({"type": "ticketProgress", "attrs": {"title": title} if title else {}})
            elif name == "whiteboard" and attrs.get("id"):
                out.append({"type": "whiteboard", "attrs": {"whiteboard": attrs["id"]}})
            elif name == "calendar" and attrs.get("id"):
                cal = {"calendar": attrs["id"]}
                if attrs.get("view") in ("month", "week"):
                    cal["view"] = attrs["view"]
                out.append({"type": "calendar", "attrs": cal})
        else:
            out += _container(item, parent)
    return out


def _container(c: _Container, parent: str) -> list[Node]:
    inner = _convert(c.items, c.name) or [_empty()]
    if c.name == "panel":
        kind = c.attrs.get("kind")
        kind = kind if kind in schema.PANEL_KINDS else "info"
        return [{"type": "panel", "attrs": {"kind": kind}, "content": inner}]
    if c.name == "expand":
        attrs = {"title": c.attrs["title"]} if c.attrs.get("title") else {}
        node: Node = {"type": "expand", "content": inner}
        if attrs:
            node["attrs"] = attrs
        return [node]
    if c.name == "columns":
        columns = [n for n in inner if n["type"] == "column"][:3]
        if len(columns) < 2:
            return [n for col in columns for n in col["content"]] or inner
        layout = c.attrs.get("layout")
        if layout not in schema.COLUMN_LAYOUTS:
            layout = "three" if len(columns) == 3 else "two"
        return [{"type": "columns", "attrs": {"layout": layout}, "content": columns}]
    if c.name == "compare":
        sides = [n for n in inner if n["type"] == "comparisonSide"][:3]
        if len(sides) < 2:
            return [n for side in sides for n in side["content"]] or inner
        return [{"type": "comparison", "content": sides}]
    if c.name == "side":
        if parent != "compare":
            return inner
        side: Node = {"type": "comparisonSide", "content": inner}
        if c.attrs.get("title"):
            side["attrs"] = {"title": c.attrs["title"]}
        return [side]
    # A column only means something inside columns; elsewhere it keeps its content.
    return [{"type": "column", "content": inner}] if parent == "columns" else inner


def from_markdown(markdown: str) -> Node:
    """A valid Folio document; unknown or misplaced directives degrade to their content."""
    return schema.validate({"type": "doc", "content": _convert(_segments(markdown))})
