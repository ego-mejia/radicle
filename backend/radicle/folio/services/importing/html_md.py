"""HTML to Folio Markdown, for exports that are web pages (Confluence). Headings,
paragraphs, emphasis, links, lists, tables, code, quotes and images survive; layout,
scripts and styles don't. Images and links pass through `resolve`, so the importer can
turn the export's files into attachments."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID = {"br", "hr", "img", "input", "meta", "link", "col", "area", "base", "source", "wbr"}
SKIP = {"script", "style", "head", "title", "noscript", "button", "form", "svg", "nav"}
BLOCKS = {"p", "div", "section", "article", "main", "header", "footer", "figure", "center"}
HEADINGS = {f"h{n}": n for n in range(1, 7)}
BLOCK_TAGS = BLOCKS | set(HEADINGS) | {"ul", "ol", "table", "pre", "blockquote", "hr"}

# (target, is_image) -> replacement Markdown, or None to keep a link as plain text.
Resolve = Callable[[str, str, bool], str | None]


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)

    def find_all(self, test: Callable[["Node"], bool]) -> list["Node"]:
        out = []
        for child in self.children:
            if isinstance(child, Node):
                if test(child):
                    out.append(child)
                out += child.find_all(test)
        return out

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse(html: str) -> Node:
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root


def _escape(text: str) -> str:
    return re.sub(r"([\\`*_\[\]])", r"\\\1", text)


class _Writer:
    def __init__(self, resolve: Resolve) -> None:
        self.resolve = resolve

    def inline(self, node: Node | str) -> str:
        if isinstance(node, str):
            return _escape(re.sub(r"\s+", " ", node))
        tag = node.tag
        if tag in SKIP:
            return ""
        if tag == "br":
            return "  \n"
        if tag == "img":
            src = node.attrs.get("src", "")
            alt = node.attrs.get("alt", "")
            image = self.resolve(src, alt, True)
            # Alone on its own lines, so Folio reads it as an image block.
            return f"\n\n{image}\n\n" if image else ""
        inner = "".join(self.inline(c) for c in node.children)
        if tag in ("strong", "b") and inner.strip():
            return f"**{inner.strip()}**"
        if tag in ("em", "i") and inner.strip():
            return f"*{inner.strip()}*"
        if tag in ("s", "del", "strike") and inner.strip():
            return f"~~{inner.strip()}~~"
        if tag == "code":
            return f"`{node.text()}`"
        if tag == "a":
            href = node.attrs.get("href", "")
            if not href or href.startswith("#"):
                return inner
            if re.match(r"^(https?|mailto):", href):
                return f"[{inner.strip() or href}]({href})"
            return self.resolve(href, inner.strip(), False) or inner
        return inner

    def blocks(self, node: Node, depth: int = 0) -> list[str]:
        out: list[str] = []
        line: list[str] = []

        def flush() -> None:
            text = "".join(line).strip()
            if text:
                out.append(text)
            line.clear()

        for child in node.children:
            if isinstance(child, str) or not self._is_block(child):
                line.append(self.inline(child))
                continue
            flush()
            out += self.block(child, depth)
        flush()
        return out

    @staticmethod
    def _is_block(node: Node) -> bool:
        return node.tag in BLOCK_TAGS

    def block(self, node: Node, depth: int) -> list[str]:
        tag = node.tag
        if tag in SKIP:
            return []
        if tag in HEADINGS:
            text = "".join(self.inline(c) for c in node.children).strip()
            return [f"{'#' * HEADINGS[tag]} {text}"] if text else []
        if tag == "hr":
            return ["---"]
        if tag == "pre":
            return [f"```\n{node.text().strip(chr(10))}\n```"]
        if tag == "blockquote":
            inner = self.blocks(node, depth)
            return ["\n>\n".join("> " + b.replace("\n", "\n> ") for b in inner)] if inner else []
        if tag in ("ul", "ol"):
            return [self.list(node, depth)]
        if tag == "table":
            return [self.table(node)]
        return self.blocks(node, depth)

    def list(self, node: Node, depth: int) -> str:
        lines = []
        n = 0
        for item in node.children:
            if not isinstance(item, Node) or item.tag != "li":
                continue
            n += 1
            marker = f"{n}." if node.tag == "ol" else "-"
            pad = "  " * depth
            texts: list[str] = []
            nested: list[str] = []
            for child in item.children:
                if isinstance(child, Node) and child.tag in ("ul", "ol"):
                    nested.append(self.list(child, depth + 1))
                elif isinstance(child, Node) and self._is_block(child):
                    texts += self.blocks(Node("div", children=[child]), depth)
                else:
                    texts.append(self.inline(child))
            text = " ".join(t.strip() for t in texts if t.strip())
            lines.append(f"{pad}{marker} {text}".rstrip())
            lines += nested
        return "\n".join(lines)

    def table(self, node: Node) -> str:
        rows = node.find_all(lambda n: n.tag == "tr")
        grid = [
            [
                " ".join(self.inline(c) for c in cell.children).strip().replace("|", "\\|") or " "
                for cell in row.children
                if isinstance(cell, Node) and cell.tag in ("td", "th")
            ]
            for row in rows
        ]
        grid = [r for r in grid if r]
        if not grid:
            return ""
        width = max(len(r) for r in grid)
        grid = [r + [" "] * (width - len(r)) for r in grid]
        lines = ["| " + " | ".join(grid[0]) + " |", "|" + " --- |" * width]
        lines += ["| " + " | ".join(r) + " |" for r in grid[1:]]
        return "\n".join(lines)


def to_markdown(node: Node, resolve: Resolve) -> str:
    """The node's content as Markdown blocks separated by blank lines."""
    writer = _Writer(resolve)
    blocks = [b for b in writer.blocks(node) if b.strip()]
    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(blocks)).strip() + "\n"
