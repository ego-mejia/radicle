"""Notion's Markdown & CSV export into pages and databases (Folio 5.3)."""

from radicle.folio.services.importing.notion import notion_id, read_notion, title_of

ENG = "Ingenieria 0f1e2d3c4b5a69788796a5b4c3d2e1f0"
GUIDE = "Conectar un agente 11112222333344445555666677778888"
TOOLS = "AI Tools 99998888777766665555444433332222"
CURSOR = "Cursor aaaabbbbccccddddeeeeffff00001111"
PNG = b"\x89PNG\r\n\x1a\n" + b"1" * 16

EXPORT = {
    f"{ENG}.md": (
        b"# Ingenieria\n\nTodo lo del equipo.\n\n[Conectar un agente]"
        b"(Ingenieria%200f1e2d3c4b5a69788796a5b4c3d2e1f0/"
        b"Conectar%20un%20agente%2011112222333344445555666677778888.md)\n"
    ),
    f"{ENG}/{GUIDE}.md": (
        b"# Conectar un agente\n\nTags: mcp, Agents\nCreated by: Ana Lopez\n\n"
        b"Crea el agente en Admin.\n\n![Untitled](Untitled.png)\n"
    ),
    f"{ENG}/Untitled.png": PNG,
    f"{ENG}/{TOOLS}.csv": b"Name,Status\nCursor,En uso\n",
    f"{ENG}/{TOOLS}_all.csv": (
        b"Name,Status,Owner\nCursor,En uso,Ana\nClaude Code,Evaluando,Luis\n,,\n"
    ),
    f"{ENG}/{TOOLS}/{CURSOR}.md": b"# Cursor\n\nStatus: En uso\n\nNotas de Cursor.",
}


def test_ids_and_titles_come_from_the_file_name() -> None:
    assert notion_id(f"{GUIDE}.md") == "11112222333344445555666677778888"
    assert notion_id(f"{TOOLS}_all.csv") == "99998888777766665555444433332222"
    assert notion_id("Plain.md") is None
    assert title_of(f"x/{TOOLS}_all.csv") == "AI Tools"


def test_an_export_becomes_pages_and_a_database() -> None:
    bundle = read_notion(EXPORT)
    pages = {p.external_id: p for p in bundle.pages}
    eng = pages["notion:0f1e2d3c4b5a69788796a5b4c3d2e1f0"]
    guide = pages["notion:11112222333344445555666677778888"]
    assert eng.parent_id is None and eng.title == "Ingenieria"
    assert "Conectar un agente" in eng.markdown and ".md" not in eng.markdown
    assert guide.parent_id == eng.external_id
    assert guide.labels == ["mcp", "agents"] and guide.author == "Ana Lopez"
    assert (
        guide.markdown.startswith("Crea el agente") and "![Untitled](import:a1)" in guide.markdown
    )
    database = pages["notion:99998888777766665555444433332222"]
    assert database.kind == "database" and database.parent_id == eng.external_id
    assert database.columns == ["Name", "Status", "Owner"]
    assert database.rows == [["Cursor", "En uso", "Ana"], ["Claude Code", "Evaluando", "Luis"]]
    rows_folder = next(p for p in bundle.pages if p.kind == "folder")
    assert rows_folder.title == "AI Tools"
    cursor = pages["notion:aaaabbbbccccddddeeeeffff00001111"]
    assert cursor.parent_id == rows_folder.external_id and cursor.markdown == "Notas de Cursor."
    assert bundle.pages[0].title == "Ingenieria"  # parents first


def test_csv_problems_and_empty_exports() -> None:
    bad = read_notion({"Empty 99998888777766665555444433332222.csv": b"\n"})
    assert bad.pages[0].errors == ["The CSV has no header row."]
    ragged = read_notion({"T 99998888777766665555444433332222.csv": b"A,B\n1\n1,2,3\n"})
    assert ragged.pages[0].rows == [["1", ""], ["1", "2"]]
    assert read_notion({"x.png": PNG}).errors == [
        "No Notion pages (.md) or databases (.csv) were found."
    ]
