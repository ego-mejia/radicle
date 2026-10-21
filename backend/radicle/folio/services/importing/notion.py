"""Notion's "Markdown & CSV" export: pages are `Title <id>.md` with their children in a
`Title <id>/` folder, and databases are `Name <id>.csv` (or `_all.csv`). Pages keep the
Notion id, so exporting again and re-importing updates them."""

import csv
import io
import posixpath
import re

from radicle.folio.services.importing.bundle import Files, text
from radicle.folio.services.importing.files import build_tree, ordered, stem
from radicle.folio.services.importing.model import Bundle, Page, clean_label, clean_title

_ID = re.compile(r"\s+([0-9a-f]{32})$")
_PROPERTY = re.compile(r"^([A-Z][\w ]{0,40}):\s+(.+)$")
LABEL_KEYS = ("tags", "labels", "etiquetas")
AUTHOR_KEYS = ("created by", "owner", "author", "creado por", "propietario")
MAX_ROWS = 10_000


def notion_id(path: str) -> str | None:
    match = _ID.search(stem(path).removesuffix("_all"))
    return match.group(1) if match else None


def title_of(path: str) -> str:
    return _ID.sub("", stem(path).removesuffix("_all"))


def _properties(page: Page) -> None:
    """The `Key: value` lines Notion writes under the title of a database row."""
    lines = page.markdown.split("\n")
    block = []
    for line in lines:
        if not line.strip():
            break
        block.append(line)
    matches = [_PROPERTY.match(line) for line in block]
    if not block or None in matches:
        return
    for match in filter(None, matches):
        key, value = match.group(1).strip().lower(), match.group(2).strip()
        if key in LABEL_KEYS:
            page.labels += [label for v in value.split(",") if (label := clean_label(v))]
        elif key in AUTHOR_KEYS and not page.author:
            page.author = value
    page.markdown = "\n".join(lines[len(block) :]).lstrip("\n")


def _database(path: str, data: bytes) -> Page:
    page = Page(f"csv:{path}", clean_title(title_of(path)), kind="database")
    rows = list(csv.reader(io.StringIO(text(data))))
    if not rows or not any(cell.strip() for cell in rows[0]):
        page.errors.append("The CSV has no header row.")
        return page
    page.columns = [cell.strip() or f"Column {n}" for n, cell in enumerate(rows[0], start=1)]
    body = [r for r in rows[1:] if any(cell.strip() for cell in r)]
    if len(body) > MAX_ROWS:
        page.errors.append(f"Only the first {MAX_ROWS} of {len(body)} rows are imported.")
    width = len(page.columns)
    page.rows = [(r + [""] * width)[:width] for r in body[:MAX_ROWS]]
    return page


def read_notion(files: Files) -> Bundle:
    bundle = Bundle("notion")
    csvs = {p for p in files if p.lower().endswith(".csv")}
    # Notion writes a view's rows and `_all` with every row; keep only the full one.
    chosen = {p for p in csvs if (p[: -len(".csv")] + "_all.csv") not in csvs}
    leaves = {p: _database(p, files[p]) for p in sorted(chosen)}
    by_path = build_tree(bundle, files, title_of=title_of, prepare=_properties, leaves=leaves)
    if not by_path:
        bundle.errors.append("No Notion pages (.md) or databases (.csv) were found.")
    # Key every page by its Notion id when it has one, so a re-export updates it.
    new_id = {}
    for path, page in by_path.items():
        source = page.external_id.removeprefix("csv:").removeprefix("dir:")
        found = notion_id(posixpath.basename(source)) if page.kind != "folder" else None
        new_id[path] = f"notion:{found}" if found else page.external_id
    pages = {}
    for path, page in by_path.items():
        page.external_id = new_id[path]
        page.parent_id = new_id.get(page.parent_id) if page.parent_id else None
        pages[page.external_id] = page
    bundle.pages = ordered(pages)
    return bundle
