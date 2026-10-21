"""Confluence's HTML space export: `index.html` lists the page tree, each page is
`Title_<id>.html` with its body in `#main-content`, its author in the page metadata,
its labels in the labels section and its files under `attachments/<page id>/`."""

import posixpath
import re
from urllib.parse import unquote

from radicle.folio.services.importing.bundle import Files, text
from radicle.folio.services.importing.files import IMAGE_EXTS, ordered
from radicle.folio.services.importing.html_md import Node, parse, to_markdown
from radicle.folio.services.importing.model import Bundle, Page, clean_label, clean_title, file_line

_PAGE_ID = re.compile(r"_(\d+)\.html?$")
_DROP = ("toc-macro", "expand-control", "page-metadata", "aui-message-hint")
_NOTE = ("confluence-information-macro", "panel", "aui-message")


def page_key(path: str) -> str:
    match = _PAGE_ID.search(path)
    name = match.group(1) if match else posixpath.splitext(posixpath.basename(path))[0]
    return f"confluence:{name}"


def _by_id(root: Node, wanted: str) -> Node | None:
    found = root.find_all(lambda n: n.attrs.get("id") == wanted)
    return found[0] if found else None


def _tree(index: Node, directory: str) -> dict[str, str | None]:
    """Each page's parent (by path) from the nested list on index.html."""
    parents: dict[str, str | None] = {}

    def walk(ul: Node, parent: str | None) -> None:
        for li in ul.children:
            if not isinstance(li, Node) or li.tag != "li":
                continue
            links = [c for c in li.children if isinstance(c, Node) and c.tag == "a"]
            href = links[0].attrs.get("href", "") if links else ""
            path = posixpath.normpath(posixpath.join(directory, unquote(href))) if href else None
            if path:
                parents.setdefault(path, parent)
            for child in li.children:
                if isinstance(child, Node) and child.tag == "ul":
                    walk(child, path or parent)

    for ul in index.find_all(lambda n: n.tag == "ul"):
        if any(isinstance(c, Node) and c.tag == "li" for c in ul.children):
            walk(ul, None)
            break
    return parents


def _clean(body: Node) -> None:
    """Drop Confluence chrome inside the body and turn info panels into quotes."""
    for node in body.find_all(lambda n: True):
        classes = node.classes()
        if classes & set(_DROP):
            node.children = []
        elif classes & set(_NOTE) and node.tag == "div" and "code" not in classes:
            node.tag = "blockquote"


def _labels(root: Node) -> list[str]:
    sections = root.find_all(
        lambda n: "labels" in n.attrs.get("id", "") or "labels" in n.attrs.get("class", "")
    )
    out: list[str] = []
    for section in sections:
        for link in section.find_all(lambda n: n.tag == "a"):
            if (label := clean_label(link.text())) and label not in out:
                out.append(label)
    return out


def _attachment_names(root: Node, directory: str) -> dict[str, str]:
    """Confluence stores files by id; their names are in the links that point at them."""
    names: dict[str, str] = {}
    for link in root.find_all(lambda n: n.tag == "a" and "attachments/" in n.attrs.get("href", "")):
        path = posixpath.normpath(posixpath.join(directory, unquote(link.attrs["href"])))
        name = link.attrs.get("data-linked-resource-default-alias") or link.text().strip()
        if "." in name and "/" not in name:
            names.setdefault(path, name[:200])
    return names


def _page(path: str, files: Files, bundle: Bundle) -> Page:
    root = parse(text(files[path]))
    directory = posixpath.dirname(path)
    heading = _by_id(root, "title-text")
    titles = root.find_all(lambda n: n.tag == "title")
    raw_title = (heading or (titles[0] if titles else Node("x"))).text()
    title = clean_title(raw_title.split(" : ", 1)[-1], posixpath.basename(path))
    author = root.find_all(lambda n: "author" in n.classes())
    page = Page(page_key(path), title, labels=_labels(root))
    page.author = (" ".join(author[0].text().split()) or None) if author else None
    files_used: list[str] = []
    names = _attachment_names(root, directory)

    def resolve(target: str, label: str, is_image: bool) -> str | None:
        found = posixpath.normpath(posixpath.join(directory, unquote(target.split("?")[0])))
        if found.startswith("images/") or "/images/icons/" in found or found.endswith(".html"):
            return None  # Confluence's own icons, and links between pages (text only)
        if found not in files:
            page.errors.append(f"Missing file: {target}")
            return None
        ref = bundle.attach(found, files[found], names.get(found))
        if is_image and found.lower().endswith(IMAGE_EXTS):
            return f"![{label}](import:{ref})"
        if ref not in files_used:
            files_used.append(ref)
        return label

    body = _by_id(root, "main-content")
    if body is None:
        page.errors.append("The page has no #main-content; is this a Confluence export?")
        body = Node("div")
    _clean(body)
    markdown = to_markdown(body, resolve)
    # Files listed in the page's Attachments section that the body doesn't show.
    prefix = posixpath.join(directory, "attachments", page_key(path).split(":", 1)[1]) + "/"
    for name in sorted(p for p in files if p.startswith(prefix)):
        ref = bundle.attach(name, files[name], names.get(name))
        if f"import:{ref})" not in markdown and ref not in files_used:
            files_used.append(ref)
    lines = [file_line(ref, bundle.attachments[ref].name) for ref in files_used]
    page.markdown = markdown + ("\n" + "\n\n".join(lines) + "\n" if lines else "")
    return page


def read_confluence(files: Files) -> Bundle:
    bundle = Bundle("confluence")
    html = sorted(p for p in files if p.lower().endswith((".html", ".htm")))
    parents: dict[str, str | None] = {}
    for index in (p for p in html if posixpath.basename(p) == "index.html"):
        parents |= _tree(parse(text(files[index])), posixpath.dirname(index))
    pages: dict[str, Page] = {}
    for path in html:
        if posixpath.basename(path) == "index.html":
            continue
        pages[path] = _page(path, files, bundle)
    if not pages:
        bundle.errors.append("No Confluence pages (.html) were found. Export the space as HTML.")
    for path, page in pages.items():
        parent = parents.get(path)
        page.parent_id = pages[parent].external_id if parent in pages else None
    # Pages in the order of the space's tree, the rest after.
    ordered_paths = [p for p in parents if p in pages] + [p for p in pages if p not in parents]
    bundle.pages = ordered({pages[p].external_id: pages[p] for p in ordered_paths})
    return bundle
