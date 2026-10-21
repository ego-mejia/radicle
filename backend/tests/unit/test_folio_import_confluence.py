"""Confluence's HTML space export into pages (Folio 5.3)."""

from radicle.folio.services.importing.confluence import read_confluence
from tests.folio_import_fixtures import load


def test_a_space_export_becomes_its_tree() -> None:
    bundle = read_confluence(load("confluence"))
    assert [(p.title, p.parent_id) for p in bundle.pages] == [
        ("Home", None),
        ("Guías", "confluence:65538"),
        ("Conectar un agente", "confluence:65540"),
        ("Decisiones", "confluence:65538"),
    ]
    home, guides, guide, decisions = bundle.pages
    assert home.author == "fernando@example.com" and guide.author == "Ana López"
    assert "Bienvenido al space de **Ingeniería**." in home.markdown
    assert "las guías" in home.markdown and "[el sitio](https://radicle.dev)" in home.markdown
    assert "Home-Guias" not in home.markdown  # the table of contents macro is dropped
    assert "1. Instalar\n2. Conectar un agente\n  - Con un token" in guides.markdown
    assert guide.labels == ["mcp", "agentes"]
    assert "# Pasos" in guide.markdown and "![flow.png](import:a1)" in guide.markdown
    assert "> El token se ve una sola vez." in guide.markdown
    assert "```\nclaude mcp add radicle --transport http\n```" in guide.markdown
    assert "| URL | `/mcp` |" in guide.markdown
    assert '::file{asset=import:a2 name="spec.pdf"}' in guide.markdown
    assert '::file{asset=import:a3 name="notas.txt"}' in guide.markdown
    assert guide.markdown.count("import:a1") == 1  # shown in the body, not listed again
    assert guide.errors == ["Missing file: attachments/65541/99999.png"]
    assert decisions.title == "Decisiones" and decisions.author is None
    assert sorted(a.name for a in bundle.attachments.values()) == [
        "flow.png",
        "notas.txt",
        "spec.pdf",
    ]


def test_not_a_confluence_export() -> None:
    assert read_confluence({"a.txt": b"x"}).errors == [
        "No Confluence pages (.html) were found. Export the space as HTML."
    ]
    page = read_confluence({"p_1.html": b"<p>hola</p>"}).pages[0]
    assert page.errors == ["The page has no #main-content; is this a Confluence export?"]
