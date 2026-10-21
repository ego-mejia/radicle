"""Folio documents to Markdown and plain text (Folio 1.2). The MCP hands agents Markdown,
exports use it, and search and the RAG index use the plain text.

Markdown has no syntax for some blocks, so they use directives (documented in
`docs/folio/markdown.md`):

    :::panel{kind=warning}          ::::columns{layout=two}     [[toc]]
    Text                            :::column                   [[children]]
    :::                             Left                        ::file{asset=a1 name="x.pdf"}
                                    :::                         ::video{src="https://..."}
    :::expand{title="More"}         :::column
    Hidden text                     Right                       :status[Done]{color=green}
    :::                             :::                         :u[underlined]
                                    ::::                        @handle (a mention)
                                                                :ticket[PA-4]

The visual blocks of phase 3 are fences (```visual{format=svg description="..."},
```mermaid, ```math, ```chart{kind=bar}, ```timeline), ::::compare with :::side, and
::pages{label=...}. Phase 4 adds ::tickets{rql="..."} (a Docket ticket table).

Images keep size and alignment as `![alt](src "caption"){size=large align=center}`.
Tables become GFM tables; merged cells, widths and cell colors don't survive Markdown.
"""

import re
from typing import Any

Node = dict[str, Any]

_ESCAPE = re.compile(r"([\\`*_\[\]<>~|])")


def _escape(text: str) -> str:
    return _ESCAPE.sub(r"\\\1", text)


def _quote(value: object) -> str:
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:#-]+", text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _attrs(**values: object) -> str:
    parts = [f"{k}={_quote(v)}" for k, v in values.items() if v not in (None, "")]
    return "{" + " ".join(parts) + "}" if parts else ""


def _marked(text: str, marks: list[Node]) -> str:
    kinds = {m["type"]: m for m in marks}
    if "code" in kinds:
        fence = "``" if "`" in text else "`"
        out = f"{fence}{text}{fence}"
    else:
        out = _escape(text)
        if "bold" in kinds:
            out = f"**{out}**"
        if "italic" in kinds:
            out = f"*{out}*"
        if "strike" in kinds:
            out = f"~~{out}~~"
        if "underline" in kinds:
            out = f":u[{out}]"
    if "link" in kinds:
        out = f"[{out}]({kinds['link']['attrs']['href']})"
    return out


def inline(nodes: list[Node]) -> str:
    out = []
    for node in nodes:
        kind = node["type"]
        attrs = node.get("attrs") or {}
        if kind == "text":
            out.append(_marked(node["text"], node.get("marks", [])))
        elif kind == "hardBreak":
            out.append("\\\n")
        elif kind == "mention":
            out.append(f"@{attrs['handle']}")
        elif kind == "status":
            out.append(f":status[{_escape(attrs['text'])}]{_attrs(color=attrs.get('color'))}")
        elif kind == "inlineFormula":
            out.append(f"${_code_span(attrs['latex'])}$")
        elif kind == "ticket":
            out.append(f":ticket[{attrs['key']}]")
    return "".join(out)


def _code_span(text: str) -> str:
    """`text` with enough backticks around it, and spaces when it starts or ends with one."""
    ticks = "`" * (max((len(r) for r in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{ticks}{pad}{text}{pad}{ticks}"


def _indent(text: str, prefix: str, first: str | None = None) -> str:
    lines = text.split("\n")
    head = first if first is not None else prefix
    return "\n".join([head + lines[0]] + [(prefix + line) if line else "" for line in lines[1:]])


def _list(node: Node, depth: int) -> str:
    items = []
    start = (node.get("attrs") or {}).get("start") or 1
    for i, item in enumerate(node.get("content", [])):
        if node["type"] == "orderedList":
            marker = f"{start + i}. "
        elif node["type"] == "taskList":
            marker = "- [x] " if (item.get("attrs") or {}).get("checked") else "- [ ] "
        else:
            marker = "- "
        body = "\n".join(block(b, depth) for b in item.get("content", []))
        items.append(_indent(body, " " * len(marker), marker))
    return "\n".join(items)


def _cell(cell: Node) -> str:
    text = " ".join(inline(b.get("content", [])) for b in cell.get("content", []))
    return text.replace("\n", " ")


def _table(node: Node) -> str:
    rows = [[_cell(c) for c in row.get("content", [])] for row in node.get("content", [])]
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def block(node: Node, depth: int = 0) -> str:
    kind = node["type"]
    attrs = node.get("attrs") or {}
    content = node.get("content", [])
    fence = ":" * (3 + depth)
    if kind == "paragraph":
        return inline(content)
    if kind == "heading":
        return "#" * int(attrs["level"]) + " " + inline(content)
    if kind in ("bulletList", "orderedList", "taskList"):
        return _list(node, depth)
    if kind == "blockquote":
        return "\n".join(
            f"> {line}" if line else ">" for line in blocks(content, depth).split("\n")
        )
    if kind == "codeBlock":
        code = "".join(c["text"] for c in content)
        ticks = "````" if "```" in code else "```"
        return f"{ticks}{attrs.get('language') or ''}\n{code}\n{ticks}"
    if kind == "horizontalRule":
        return "---"
    if kind == "actionItem":
        extra = _attrs(
            id=attrs["id"],
            assignee=attrs.get("assignee"),
            due=attrs.get("due"),
            done="true" if attrs.get("done") else None,
        )
        return f"::task[{inline(content)}]{extra}"
    if kind == "table":
        return _table(node)
    if kind == "panel":
        return f"{fence}panel{_attrs(kind=attrs['kind'])}\n{blocks(content, depth + 1)}\n{fence}"
    if kind == "expand":
        head = f"{fence}expand{_attrs(title=attrs.get('title'))}"
        return f"{head}\n{blocks(content, depth + 1)}\n{fence}"
    if kind == "columns":
        outer = ":" * (4 + depth)
        inner = ":" * (3 + depth)
        cols = [
            f"{inner}column\n{blocks(c.get('content', []), depth + 1)}\n{inner}" for c in content
        ]
        return f"{outer}columns{_attrs(layout=attrs['layout'])}\n" + "\n".join(cols) + f"\n{outer}"
    if kind == "tableOfContents":
        return "[[toc]]"
    if kind == "childPages":
        return "[[children]]"
    if kind == "image":
        src = attrs.get("src") or (f"asset:{attrs['assetId']}" if attrs.get("assetId") else "")
        caption = f' "{attrs["caption"]}"' if attrs.get("caption") else ""
        extra = _attrs(size=attrs.get("size"), align=attrs.get("align"))
        return f"![{_escape(attrs.get('alt') or '')}]({src}{caption}){extra}"
    if kind == "file":
        return "::file" + _attrs(
            asset=attrs["assetId"],
            name=attrs.get("name"),
            type=attrs.get("mimeType"),
            size=attrs.get("size"),
        )
    if kind == "video":
        return "::video" + _attrs(
            src=attrs.get("src"), asset=attrs.get("assetId"), caption=attrs.get("caption")
        )
    if kind == "visual":
        head = "visual" + _attrs(
            format=attrs["format"], title=attrs.get("title"), description=attrs["description"]
        )
        return _fenced(head, attrs["code"])
    if kind == "diagram":
        return _fenced(attrs["language"] + _attrs(caption=attrs.get("caption")), attrs["source"])
    if kind == "formula":
        return _fenced("math", attrs["latex"])
    if kind == "chart" and attrs.get("source") == "table":
        return _fenced(
            "chart" + _attrs(kind=attrs["kind"], title=attrs.get("title"), source="table"), ""
        )
    if kind == "chart":
        rows = [[str(c) for c in row] for row in attrs["data"]]
        table = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(["---"] * len(rows[0])) + "|"]
        table += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        head = "chart" + _attrs(kind=attrs["kind"], title=attrs.get("title"))
        return _fenced(head, "\n".join(table))
    if kind == "timeline":
        boxes = {"done": "[x] ", "in_progress": "[~] ", "planned": "[ ] "}
        lines = [
            boxes.get(i.get("status", ""), "")
            + " | ".join([i.get("date", ""), i["title"], i.get("text", "")]).rstrip(" |")
            for i in attrs["items"]
        ]
        return _fenced("timeline", "\n".join(lines))
    if kind == "comparison":
        outer = ":" * (4 + depth)
        inner = ":" * (3 + depth)
        sides = [
            f"{inner}side{_attrs(title=(c.get('attrs') or {}).get('title'))}\n"
            f"{blocks(c.get('content', []), depth + 1)}\n{inner}"
            for c in content
        ]
        return f"{outer}compare\n" + "\n".join(sides) + f"\n{outer}"
    if kind == "pageList":
        return "::pages" + _attrs(
            label=attrs["label"],
            limit=attrs.get("limit"),
            space=attrs.get("space"),
            order=attrs.get("order"),
        )
    if kind == "ticketTable":
        return "::tickets" + _attrs(
            rql=attrs["rql"], title=attrs.get("title"), limit=attrs.get("limit")
        )
    if kind == "databaseView":
        return "::database" + _attrs(id=attrs["database"], view=attrs.get("view"))
    if kind == "whiteboard":
        return "::whiteboard" + _attrs(id=attrs["whiteboard"])
    if kind == "embed":
        return "::embed" + _attrs(url=attrs["url"], title=attrs.get("title"))
    return ""


def _fenced(info: str, body: str) -> str:
    """A fenced block long enough not to end inside its body."""
    ticks = "`" * max(3, max((len(m) for m in re.findall(r"`{3,}", body)), default=0) + 1)
    return f"{ticks}{info}\n{body}\n{ticks}"


def blocks(nodes: list[Node], depth: int = 0) -> str:
    return "\n\n".join(b for b in (block(n, depth) for n in nodes) if b != "")


def to_markdown(doc: Node) -> str:
    return blocks(doc.get("content", [])) + "\n" if doc.get("content") else ""


_LINES = (
    "paragraph",
    "actionItem",
    "heading",
    "codeBlock",
    "tableCell",
    "tableHeader",
    "listItem",
    "image",
    "file",
    "video",
    "embed",
)


def _text_of(node: Node, out: list[str]) -> None:
    kind = node["type"]
    attrs = node.get("attrs") or {}
    if kind == "text":
        out.append(node["text"])
    elif kind == "hardBreak":
        out.append("\n")
    elif kind == "mention":
        out.append(f"@{attrs['handle']}")
    elif kind == "status":
        out.append(attrs["text"])
    elif kind == "inlineFormula":
        out.append(attrs["latex"])
    elif kind == "ticket":
        out.append(attrs["key"])
    elif kind == "ticketTable" and attrs.get("title"):
        out.append(attrs["title"] + "\n")
    elif kind == "image":
        out.append(" ".join(v for v in (attrs.get("alt"), attrs.get("caption")) if v))
    elif kind in ("file", "video"):
        out.append(attrs.get("name") or attrs.get("caption") or "")
    elif kind == "embed":
        out.append(attrs.get("title") or attrs["url"])
    elif kind == "expand" and attrs.get("title"):
        out.append(attrs["title"] + "\n")
    elif kind == "comparisonSide" and attrs.get("title"):
        out.append(attrs["title"] + "\n")
    elif kind == "visual":
        out.append(" ".join(v for v in (attrs.get("title"), attrs["description"]) if v) + "\n")
    elif kind == "diagram":
        out.append(" ".join(v for v in (attrs.get("caption"), attrs["source"]) if v) + "\n")
    elif kind == "formula":
        out.append(attrs["latex"] + "\n")
    elif kind == "chart":
        rows = [" ".join(str(c) for c in row) for row in attrs.get("data") or []]
        out.append("\n".join([attrs.get("title") or "", *rows]).strip() + "\n")
    elif kind == "timeline":
        keys = ("date", "title", "text")
        items = (" ".join(i[k] for k in keys if i.get(k)) for i in attrs["items"])
        out.append("\n".join(items) + "\n")
    for child in node.get("content", []):
        _text_of(child, out)
    if kind in _LINES:
        out.append("\n")


def to_text(doc: Node) -> str:
    """Plain text for search: one line per paragraph, cell or list item, no markup."""
    out: list[str] = []
    for node in doc.get("content", []):
        _text_of(node, out)
    text = "".join(out)
    return re.sub(r"\n{2,}", "\n", text).strip()
