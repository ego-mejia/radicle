"""A Folio document (TipTap JSON) as static HTML, for exports read outside Radicle.

Everything is escaped. Visuals keep their sandbox (an iframe with scripts and no origin);
blocks that show live Radicle data (ticket tables, page lists, databases, whiteboards,
calendars) become a note, since a file can't ask Radicle for them.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape
from typing import Any

Node = dict[str, Any]
LIVE = {"pageList", "ticketTable", "ticketProgress", "databaseView", "whiteboard", "calendar"}
VISUAL_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "img-src data:; font-src data:"
)


@dataclass
class Links:
    asset: Callable[[str], str | None]  # where an asset is; None if the export lacks it
    children: list[tuple[str, str]] = field(default_factory=list)  # (title, href) below


def _a(value: object) -> str:
    return escape(str(value), quote=True)


def _t(value: object) -> str:
    return escape(str(value))


def _box(checked: object) -> str:
    return f'<input type="checkbox" disabled{" checked" if checked else ""}>'


def _inline(nodes: list[Node]) -> str:
    out = []
    for n in nodes:
        kind, attrs = n.get("type"), n.get("attrs") or {}
        if kind == "text":
            text = escape(n.get("text", ""))
            for mark in n.get("marks") or []:
                m = mark.get("type")
                if m == "bold":
                    text = f"<strong>{text}</strong>"
                elif m == "italic":
                    text = f"<em>{text}</em>"
                elif m == "strike":
                    text = f"<s>{text}</s>"
                elif m == "underline":
                    text = f"<u>{text}</u>"
                elif m == "code":
                    text = f"<code>{text}</code>"
                elif m == "link":
                    href = str((mark.get("attrs") or {}).get("href", ""))
                    if href.startswith(("http://", "https://", "mailto:", "#")):
                        text = f'<a href="{_a(href)}" rel="noopener">{text}</a>'
            out.append(text)
        elif kind == "hardBreak":
            out.append("<br>")
        elif kind == "mention":
            out.append(f'<span class="mention">@{escape(str(attrs.get("handle", "")))}</span>')
        elif kind == "status":
            out.append(f'<span class="status">{escape(str(attrs.get("text", "")))}</span>')
        elif kind == "ticket":
            out.append(f'<span class="ticket">{escape(str(attrs.get("key", "")))}</span>')
        elif kind == "inlineFormula":
            out.append(f'<code class="formula">{escape(str(attrs.get("latex", "")))}</code>')
    return "".join(out)


def text_of(node: Node) -> str:
    if node.get("type") == "text":
        return str(node.get("text", ""))
    return "".join(text_of(c) for c in node.get("content") or [])


def _table(rows: list[list[Any]]) -> str:
    head, *body = rows
    th = "".join(f"<th>{escape(str(c))}</th>" for c in head)
    trs = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def render(doc: Node, links: Links) -> str:
    headings: list[tuple[int, str, str]] = []

    def blocks(nodes: list[Node], top: bool = False) -> str:
        out, previous = [], None
        for n in nodes:
            out.append(block(n, top, previous))
            previous = n
        return "".join(out)

    def block(n: Node, top: bool, previous: Node | None) -> str:
        kind, attrs, content = n.get("type"), n.get("attrs") or {}, n.get("content") or []
        if kind == "paragraph":
            return f"<p>{_inline(content)}</p>"
        if kind == "heading":
            level = min(max(int(attrs.get("level", 1)), 1), 4) + 1
            anchor = f"s{len(headings) + 1}"
            if top:
                headings.append((level, text_of(n), anchor))
            return f'<h{level} id="{anchor}">{_inline(content)}</h{level}>'
        if kind in ("bulletList", "orderedList"):
            tag = "ul" if kind == "bulletList" else "ol"
            items = "".join(f"<li>{blocks(i.get('content') or [])}</li>" for i in content)
            return f"<{tag}>{items}</{tag}>"
        if kind == "taskList":
            items = "".join(
                f"<li>{_box((i.get('attrs') or {}).get('checked'))} "
                f"{blocks(i.get('content') or [])}</li>"
                for i in content
            )
            return f'<ul class="tasks">{items}</ul>'
        if kind == "actionItem":
            due = f" <small>({_t(attrs['due'])})</small>" if attrs.get("due") else ""
            return f'<p class="action">{_box(attrs.get("done"))} {_inline(content)}{due}</p>'
        if kind == "blockquote":
            return f"<blockquote>{blocks(content)}</blockquote>"
        if kind == "codeBlock":
            lang = f' data-language="{_a(attrs["language"])}"' if attrs.get("language") else ""
            return f"<pre{lang}><code>{escape(text_of(n))}</code></pre>"
        if kind == "horizontalRule":
            return "<hr>"
        if kind == "table":
            rows = []
            for row in content:
                cells = []
                for cell in row.get("content") or []:
                    tag = "th" if cell.get("type") == "tableHeader" else "td"
                    cells.append(f"<{tag}>{blocks(cell.get('content') or [])}</{tag}>")
                rows.append("<tr>" + "".join(cells) + "</tr>")
            return f"<table>{''.join(rows)}</table>"
        if kind == "panel":
            return f'<div class="panel {_a(attrs.get("kind", "info"))}">{blocks(content)}</div>'
        if kind == "expand":
            title = escape(str(attrs.get("title") or "…"))
            return f"<details><summary>{title}</summary>{blocks(content)}</details>"
        if kind in ("columns", "comparison"):
            cols = []
            for col in content:
                side = (col.get("attrs") or {}).get("title")
                head = f"<h4>{_t(side)}</h4>" if side else ""
                cols.append(f"<div>{head}{blocks(col.get('content') or [])}</div>")
            return f'<div class="columns">{"".join(cols)}</div>'
        if kind == "tableOfContents":
            return "<!--toc-->"
        if kind == "childPages":
            items = "".join(
                f'<li><a href="{_a(h)}">{escape(t)}</a></li>' for t, h in links.children
            )
            return f'<ul class="children">{items}</ul>' if items else ""
        if kind in ("image", "video", "file"):
            src = links.asset(str(attrs["assetId"])) if attrs.get("assetId") else attrs.get("src")
            if not src:
                return ""
            if kind == "file":
                name = _t(attrs.get("name") or src)
                return f'<p class="file"><a href="{_a(src)}">{name}</a></p>'
            caption = (
                f"<figcaption>{escape(str(attrs['caption']))}</figcaption>"
                if attrs.get("caption")
                else ""
            )
            media = (
                f'<img src="{_a(src)}" alt="{_a(attrs.get("alt") or "")}">'
                if kind == "image"
                else f'<video src="{_a(src)}" controls></video>'
            )
            return f"<figure>{media}{caption}</figure>"
        if kind == "visual":
            code = str(attrs.get("code", ""))
            page = f'<meta http-equiv="Content-Security-Policy" content="{VISUAL_CSP}">{code}'
            title = escape(str(attrs.get("title") or ""))
            return (
                f'<figure class="visual"><iframe sandbox="allow-scripts" title="{title}" '
                f'srcdoc="{_a(page)}"></iframe>'
                f"<figcaption>{escape(str(attrs.get('description', '')))}</figcaption></figure>"
            )
        if kind == "diagram":
            caption = (
                f"<figcaption>{escape(str(attrs['caption']))}</figcaption>"
                if attrs.get("caption")
                else ""
            )
            source = _t(attrs.get("source", ""))
            return f'<figure class="diagram"><pre>{source}</pre>{caption}</figure>'
        if kind == "formula":
            return f'<pre class="formula">{escape(str(attrs.get("latex", "")))}</pre>'
        if kind == "chart":
            data: list[list[Any]] | None = attrs.get("data")
            if attrs.get("source") == "table" and previous and previous.get("type") == "table":
                data = [
                    [text_of(c) for c in r.get("content") or []]
                    for r in previous.get("content") or []
                ]
            heading = f"<h4>{_t(attrs['title'])}</h4>" if attrs.get("title") else ""
            return f'<figure class="chart">{heading}{_table(data) if data else ""}</figure>'
        if kind == "timeline":
            items = "".join(
                f"<li><strong>{_t(i.get('date', ''))}</strong> {_t(i.get('title', ''))}"
                f"{' — ' + escape(str(i['text'])) if i.get('text') else ''}</li>"
                for i in attrs.get("items") or []
            )
            return f'<ol class="timeline">{items}</ol>'
        if kind == "embed":
            url = str(attrs.get("url", ""))
            label = _t(attrs.get("title") or url)
            return f'<p class="embed"><a href="{_a(url)}" rel="noopener">{label}</a></p>'
        if kind in LIVE:
            return (
                '<p class="live">Live content from Radicle: open the page in Radicle to see it.</p>'
            )
        return blocks(content) if content else ""

    body = blocks(doc.get("content") or [], top=True)
    if "<!--toc-->" in body:
        toc = "".join(
            f'<li class="h{level}"><a href="#{a}">{escape(t)}</a></li>' for level, t, a in headings
        )
        body = body.replace("<!--toc-->", f'<nav class="toc"><ul>{toc}</ul></nav>')
    return body
