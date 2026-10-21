"""Exports made of Markdown files in folders (a Markdown folder, Notion): the folder tree
becomes the page tree, and relative images and files become attachments."""

import posixpath
import re
from collections.abc import Callable
from urllib.parse import unquote

from radicle.folio.services.importing.bundle import Files, text
from radicle.folio.services.importing.model import Bundle, Page, clean_label, clean_title, file_line

PAGE_EXTS = (".md", ".markdown")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
_LINK = re.compile(r"(!?)\[([^\]]*)\]\(<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\)")
_HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)

# A page's title from its path, and its body Markdown before references are rewritten.
TitleOf = Callable[[str], str]


def is_page(path: str) -> bool:
    return path.lower().endswith(PAGE_EXTS)


def stem(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    for ext in (*PAGE_EXTS, ".csv", ".docx"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name


def front_matter(markdown: str) -> tuple[dict[str, str | list[str]], str]:
    """Simple YAML front matter (`key: value`, `[a, b]` or `- a` lists) and the rest."""
    if not markdown.startswith("---\n"):
        return {}, markdown
    end = markdown.find("\n---", 4)
    if end < 0:
        return {}, markdown
    meta: dict[str, str | list[str]] = {}
    key = None
    for line in markdown[4:end].splitlines():
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key:
            current = meta.get(key)
            values = current if isinstance(current, list) else []
            meta[key] = [*values, item.group(1).strip().strip("'\"")]
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not pair:
            continue
        key, value = pair.group(1).lower(), pair.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key] = value.strip("'\"")
    return meta, markdown[end + 4 :].lstrip("\n")


def take_title(markdown: str) -> tuple[str | None, str]:
    """The first `# heading` as the title, removed from the body."""
    lines = markdown.lstrip("\n").split("\n")
    match = _HEADING.match(lines[0]) if lines else None
    if match:
        return match.group(1), "\n".join(lines[1:]).lstrip("\n")
    return None, markdown


def rewrite_refs(page: Page, path: str, files: Files, bundle: Bundle) -> None:
    """Relative images and files become attachments; links to other pages keep their text."""
    base = posixpath.dirname(path)
    out: list[str] = []
    for line in page.markdown.split("\n"):
        extra: list[str] = []
        only_image = bool(re.fullmatch(r"\s*!\[[^\]]*\]\([^)]*\)\s*", line))

        def replace(m: re.Match[str], extra: list[str] = extra, alone: bool = only_image) -> str:
            bang, label, target = m.group(1), m.group(2), m.group(3)
            if _SCHEME.match(target) or target.startswith("#"):
                return m.group(0)
            found = posixpath.normpath(posixpath.join(base, unquote(target.split("#")[0])))
            if found not in files:
                page.errors.append(f"Missing file: {unquote(target)}")
                return label
            if is_page(found) or found.lower().endswith(".csv"):
                return label  # links between pages aren't kept: only their text
            ref = bundle.attach(found, files[found])
            if bang and found.lower().endswith(IMAGE_EXTS):
                image = f"![{label}](import:{ref})"
                if alone:
                    return image
                extra.append(image)
                return ""
            extra.append(file_line(ref, found.rsplit("/", 1)[-1]))
            return label

        out.append(_LINK.sub(replace, line))
        if extra:
            out.extend(["", *extra, ""])
    page.markdown = "\n".join(out)


def labels_from(meta: dict[str, str | list[str]]) -> list[str]:
    raw = meta.get("labels") or meta.get("tags") or []
    values = raw if isinstance(raw, list) else raw.split(",")
    return [label for v in values if (label := clean_label(v))]


def build_tree(
    bundle: Bundle,
    files: Files,
    *,
    title_of: TitleOf = stem,
    index_names: tuple[str, ...] = ("index.md", "readme.md"),
) -> dict[str, Page]:
    """A page per Markdown file and a folder per directory, nested as on disk. A directory
    next to `X.md` (Notion) or holding an index file becomes that page's children."""
    paths = sorted(p for p in files if is_page(p))
    pages: dict[str, Page] = {}
    owner: dict[str, str] = {}  # directory -> external id of the page that holds it
    for path in paths:
        directory, name = posixpath.split(path)
        if name.lower() in index_names and directory:
            owner[directory] = path
        else:
            sibling = posixpath.splitext(path)[0]
            if any(p.startswith(sibling + "/") for p in files):
                owner.setdefault(sibling, path)

    def parent_of(directory: str) -> str | None:
        if not directory:
            return None
        if directory in owner:
            return owner[directory]
        key = f"dir:{directory}"
        if key not in pages:
            pages[key] = Page(
                key,
                clean_title(title_of(directory)),
                parent_id=parent_of(posixpath.dirname(directory)),
                kind="folder",
            )
        return key

    for path in paths:
        directory = posixpath.dirname(path)
        held = next((d for d, p in owner.items() if p == path), None)
        parent_dir = posixpath.dirname(held) if held is not None else directory
        meta, body = front_matter(text(files[path]))
        heading, body = take_title(body)
        fallback = title_of(held if held is not None else path)
        page = Page(
            path,
            clean_title(str(meta.get("title") or heading or fallback)),
            markdown=body,
            labels=labels_from(meta),
            author=str(meta.get("author") or meta.get("owner") or "") or None,
        )
        pages[path] = page
        page.parent_id = parent_of(parent_dir)
    for path, page in list(pages.items()):
        if page.kind == "page":
            rewrite_refs(page, path, files, bundle)
    return pages


def read_markdown(files: Files) -> Bundle:
    bundle = Bundle("markdown")
    pages = build_tree(bundle, files)
    if not pages:
        bundle.errors.append("No Markdown files (.md) were found in the upload.")
    bundle.pages = ordered(pages)
    return bundle


def ordered(pages: dict[str, Page]) -> list[Page]:
    """Parents before their children, so the run can create them in one pass."""
    out: list[Page] = []
    seen: set[str] = set()

    def visit(page: Page) -> None:
        if page.external_id in seen:
            return
        if page.parent_id and page.parent_id in pages:
            visit(pages[page.parent_id])
        seen.add(page.external_id)
        out.append(page)

    for key in sorted(pages, key=lambda k: k.removeprefix("dir:")):
        visit(pages[key])
    return out
