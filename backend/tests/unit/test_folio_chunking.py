"""Chunking (Folio 1.6): sections with their heading path and anchor, long sections split
without cutting tables, code or lists."""

from radicle.folio.services import chunking
from tests.unit.folio_docs import EVERY_BLOCK, block, p, t


def doc(*blocks: dict) -> dict:
    return {"type": "doc", "content": list(blocks)}


def h(level: int, text: str) -> dict:
    return block("heading", t(text), level=level)


def test_one_chunk_per_section_with_path_and_anchor() -> None:
    chunks = chunking.chunk(
        doc(
            p(t("Intro")),
            h(1, "Conecta un agente"),
            p(t("Pasos.")),
            h(2, "Crea el agente"),
            p(t("En Admin.")),
            h(2, "Crea el agente"),
            p(t("Otra vez.")),
            h(1, "Después"),
        )
    )
    assert [(c.heading_path, c.anchor, c.text) for c in chunks] == [
        ([], None, "Intro"),
        (["Conecta un agente"], "conecta-un-agente", "Pasos."),
        (["Conecta un agente", "Crea el agente"], "crea-el-agente", "En Admin."),
        (["Conecta un agente", "Crea el agente"], "crea-el-agente-2", "Otra vez."),
        (["Después"], "despues", ""),
    ]
    assert [c.position for c in chunks] == [0, 1, 2, 3, 4]


def test_tables_and_code_keep_their_structure_and_media_their_captions() -> None:
    texts = [c.text for c in chunking.chunk(EVERY_BLOCK)]
    joined = "\n".join(texts)
    assert "| Campo | Regla |" in joined and "```python\nprint('hola')\n```" in joined
    assert "Diagrama El flujo" in joined and "spec.pdf" in joined
    assert "[[toc]]" not in joined and "[[children]]" not in joined
    assert "---" not in texts  # the divider adds no text of its own


def test_long_sections_split_with_overlap_but_not_through_tables() -> None:
    para = " ".join(f"palabra{i}" for i in range(300))  # ~400 tokens each
    rows = [block("tableRow", block("tableCell", p(t(f"fila {i} " * 20)))) for i in range(30)]
    table = block("table", *rows)
    chunks = chunking.chunk(doc(h(1, "Largo"), p(t(para)), p(t(para.upper())), table, p(t(para))))
    assert len(chunks) >= 3
    assert all(c.heading_path == ["Largo"] and c.anchor == "largo" for c in chunks)
    second = chunks[1].text
    assert second.startswith(" ".join(para.split()[-chunking.OVERLAP_WORDS :]))
    table_md = chunking.convert.block(table)
    assert sum(table_md in c.text for c in chunks) == 1  # the whole table, once


def test_a_huge_paragraph_is_cut_in_windows() -> None:
    huge = " ".join(f"w{i}" for i in range(2000))
    chunks = chunking.chunk(doc(p(t(huge))))
    assert len(chunks) > 3
    assert all(c.token_count <= chunking.MAX_TOKENS for c in chunks)


def test_embedding_input_starts_with_the_document() -> None:
    c = chunking.Chunk(0, ["Guía", "Paso 1"], "paso-1", "Haz esto.", 3)
    assert chunking.embedding_input("Título", "Descripción.", c) == (
        "Título\nDescripción.\nGuía > Paso 1\nHaz esto."
    )
