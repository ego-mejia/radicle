"""Reading uploads safely, and Markdown folders into pages (Folio 5.3)."""

import io
import zipfile

import pytest

from radicle.folio.services.importing import bundle
from radicle.folio.services.importing.files import front_matter, read_markdown
from radicle.platform.errors import ValidationFailed

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def make_zip(files: dict[str, bytes | str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return out.getvalue()


def test_paths_that_leave_the_archive_are_dropped() -> None:
    assert bundle.safe_path("../etc/passwd") is None
    assert bundle.safe_path("/abs/file.md") is None
    assert bundle.safe_path("C:\\x\\file.md") is None
    assert bundle.safe_path("__MACOSX/a.md") is None
    assert bundle.safe_path("a/./b\\c.md") == "a/b/c.md"
    data = make_zip({"ok.md": "# Ok", "../evil.md": "x", ".hidden/x.md": "y"})
    assert list(bundle.read("export.zip", data)) == ["ok.md"]


def test_a_zip_bomb_is_refused() -> None:
    data = make_zip({"bomb.md": "0" * (5 * 1024 * 1024)})
    with pytest.raises(ValidationFailed, match="expands too much"):
        bundle.read("export.zip", data)


def test_limits_and_single_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle, "MAX_FILES", 2)
    with pytest.raises(ValidationFailed, match="up to 2"):
        bundle.read("e.zip", make_zip({"a.md": "a", "b.md": "b", "c.md": "c"}))
    with pytest.raises(ValidationFailed, match="empty"):
        bundle.read("a.md", b"")
    assert bundle.read("notes/guide.md", b"# Hi") == {"guide.md": b"# Hi"}


def test_front_matter() -> None:
    meta, body = front_matter(
        "---\ntitle: Guía\ntags: [api, Agents]\nauthors:\n  - a@x.io\n---\nHola"
    )
    assert meta == {"title": "Guía", "tags": ["api", "Agents"], "authors": ["a@x.io"]}
    assert body == "Hola"


def test_a_markdown_folder_becomes_a_tree() -> None:
    files = {
        "README.md": b"# Inicio\n\nBienvenida.",
        "guides/index.md": b"# Guias\n\nTodas las guias.",
        "guides/connect.md": (
            b"---\ntitle: Conectar un agente\ntags: mcp, agents\nauthor: ana@example.com\n---\n"
            b"Paso uno.\n\n![Diagrama](img/flow.png)\n\nVer [el PDF](files/spec.pdf) y "
            b"[la otra guia](index.md).\n\n![Falta](img/missing.png)\n"
        ),
        "guides/img/flow.png": PNG,
        "guides/files/spec.pdf": b"%PDF-1.4",
        "notes/today.md": b"Sin titulo",
    }
    result = read_markdown(files)
    pages = {p.external_id: p for p in result.pages}
    assert [p.title for p in result.pages] == [
        "Inicio",
        "Guias",
        "Conectar un agente",
        "notes",
        "today",
    ]
    guide = pages["guides/connect.md"]
    assert guide.parent_id == "guides/index.md" and guide.author == "ana@example.com"
    assert guide.labels == ["mcp", "agents"]
    assert "![Diagrama](import:a1)" in guide.markdown
    assert '::file{asset=import:a2 name="spec.pdf"}' in guide.markdown
    assert "la otra guia" in guide.markdown and "index.md" not in guide.markdown
    assert guide.errors == ["Missing file: img/missing.png"]
    assert result.attachments["a1"].data == PNG and result.attachments["a2"].name == "spec.pdf"
    assert pages["dir:notes"].kind == "folder" and pages["notes/today.md"].parent_id == "dir:notes"


def test_an_upload_without_markdown_says_so() -> None:
    assert read_markdown({"a.png": PNG}).errors == [
        "No Markdown files (.md) were found in the upload."
    ]


def test_size_limits_and_encodings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle, "MAX_TOTAL", 3)
    with pytest.raises(ValidationFailed, match="expands to over"):
        bundle.read("e.zip", make_zip({"a.md": "ab", "b.md": "cd"}))
    monkeypatch.setattr(bundle, "MAX_FILE", 1)
    with pytest.raises(ValidationFailed, match="is over"):
        bundle.read("e.zip", make_zip({"a.md": "ab"}))
    monkeypatch.setattr(bundle, "MAX_UPLOAD", 1)
    with pytest.raises(bundle.PayloadTooLarge):
        bundle.read("e.zip", b"ab")
    assert bundle.text("café".encode("cp1252")) == "café"
    assert bundle.text("﻿hola".encode()) == "hola"
