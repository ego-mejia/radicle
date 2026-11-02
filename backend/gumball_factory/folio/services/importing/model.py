"""What every importer produces: pages with Markdown, their tree, and the files they use.

Page Markdown points at attachments as `import:<ref>` (in an image or a `::file` line);
the import run uploads each file and rewrites the ref to the new asset's id."""

import re
from dataclasses import dataclass, field
from typing import Literal

PageKind = Literal["page", "folder", "database"]
REF = re.compile(r"import:(a\d+)")


@dataclass
class Page:
    external_id: str
    title: str
    parent_id: str | None = None
    kind: PageKind = "page"
    markdown: str = ""
    labels: list[str] = field(default_factory=list)
    author: str | None = None  # an email or a display name, as the source has it
    columns: list[str] = field(default_factory=list)  # databases
    rows: list[list[str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Attachment:
    ref: str
    name: str
    data: bytes


@dataclass
class Bundle:
    source: str
    pages: list[Page] = field(default_factory=list)
    attachments: dict[str, Attachment] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)  # about the upload as a whole
    _by_path: dict[str, str] = field(default_factory=dict, repr=False)

    def attach(self, path: str, data: bytes, name: str | None = None) -> str:
        """The ref for this file, adding it once however many pages use it."""
        if path in self._by_path:
            return self._by_path[path]
        ref = f"a{len(self.attachments) + 1}"
        self.attachments[ref] = Attachment(ref, name or path.rsplit("/", 1)[-1], data)
        self._by_path[path] = ref
        return ref

    def refs(self, page: Page) -> list[str]:
        return list(dict.fromkeys(REF.findall(page.markdown)))


def file_line(ref: str, name: str) -> str:
    safe = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'::file{{asset=import:{ref} name="{safe}"}}'


def clean_title(text: str, fallback: str = "Untitled") -> str:
    title = " ".join(text.split())[:200]
    return title or fallback


def clean_label(text: str) -> str | None:
    label = re.sub(r"[^a-z0-9_-]+", "-", text.strip().lower().lstrip("#")).strip("-")[:50]
    return label or None
