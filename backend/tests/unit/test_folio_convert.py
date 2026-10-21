"""Folio documents to Markdown and plain text (Folio 1.2)."""

from pathlib import Path

from radicle.folio.services import convert
from tests.unit.folio_docs import EVERY_BLOCK, block, p, t

EXPECTED = (Path(__file__).parent / "folio_every_block.md").read_text()


def doc(*blocks: dict) -> dict:
    return {"type": "doc", "content": list(blocks)}


def test_every_block_to_markdown() -> None:
    assert convert.to_markdown(EVERY_BLOCK) == EXPECTED


def test_escapes_and_code() -> None:
    assert convert.to_markdown(doc(p(t("a*b_c [x] | y")))) == "a\\*b\\_c \\[x\\] \\| y\n"
    assert convert.to_markdown(doc(p(t("a`b", "code")))) == "``a`b``\n"
    fenced = convert.to_markdown(doc(block("codeBlock", t("```\nx\n```"))))
    assert fenced.startswith("````\n") and fenced.endswith("\n````\n")
    assert convert.to_markdown(doc(p(t("x", "bold", "italic", "strike", "underline")))) == (
        ":u[~~***x***~~]\n"
    )


def test_nested_lists_and_quotes() -> None:
    nested = block(
        "bulletList",
        block("listItem", p(t("uno")), block("orderedList", block("listItem", p(t("a"))), start=3)),
    )
    assert convert.to_markdown(doc(nested)) == "- uno\n  3. a\n"
    quote = block("blockquote", p(t("uno")), p(t("dos")))
    assert convert.to_markdown(doc(quote)) == "> uno\n>\n> dos\n"


def test_nested_directives_use_longer_fences() -> None:
    inner = block("panel", p(t("ojo")), kind="tip")
    outer = block("expand", inner, title="Más detalles")
    assert convert.to_markdown(doc(outer)) == (
        ':::expand{title="Más detalles"}\n::::panel{kind=tip}\nojo\n::::\n:::\n'
    )


def test_tables_lose_only_what_markdown_cannot_say() -> None:
    table = block(
        "table",
        block("tableRow", block("tableHeader", p(t("a|b")), colspan=2)),
        block("tableRow", block("tableCell", p(t("1"))), block("tableCell", p(t("2")))),
    )
    assert convert.to_markdown(doc(table)) == "| a\\|b |  |\n|---|---|\n| 1 | 2 |\n"


def test_images_from_assets_and_empty_documents() -> None:
    image = block("image", assetId="f00", alt="Logo")
    assert convert.to_markdown(doc(image)) == "![Logo](asset:f00)\n"
    assert convert.to_markdown({"type": "doc", "content": []}) == ""


def test_plain_text_for_search() -> None:
    text = convert.to_text(EVERY_BLOCK)
    assert text.startswith("Conecta un agente\nTexto negrita y código con link\n@fernando Listo")
    assert "print('hola')" in text and "Ojo con el token." in text
    assert text.endswith("Diagrama El flujo\nspec.pdf\nDemo\nFin")
    assert "**" not in text and ":::" not in text
