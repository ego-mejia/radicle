"""Inline comment anchors survive edits around and inside their text (Folio 2.3)."""

from radicle.folio.services import anchors

TEXT = "Intro.\nCrea el agente en Admin y conéctalo por MCP con su token.\nFin."
QUOTE = "conéctalo por MCP"


def anchor() -> anchors.Anchor:
    found = anchors.first(TEXT, QUOTE)
    assert found is not None and found.quote == QUOTE
    return found


def quote_in(text: str) -> str | None:
    moved = anchors.relocate(text, anchor())
    return moved.quote if moved else None


def test_edits_before_and_after_keep_it() -> None:
    assert quote_in(TEXT.replace("Intro.", "Una introducción mucho más larga.")) == QUOTE
    assert quote_in(TEXT.replace("Fin.", "Fin, con una nota.")) == QUOTE


def test_an_edit_inside_moves_the_quote_with_it() -> None:
    edited = TEXT.replace(QUOTE, "conéctalo desde Claude por MCP")
    assert quote_in(edited) == "conéctalo desde Claude por MCP"


def test_an_edit_to_the_context_falls_back_to_the_quote() -> None:
    moved = anchors.relocate("Otra cosa: " + QUOTE + " y nada más.", anchor())
    assert moved is not None and moved.quote == QUOTE and moved.offset == 11


def test_two_edits_at_once_inside_and_beside_it() -> None:
    edited = TEXT.replace(QUOTE, "conéctalo ya por MCP").replace("token.", "token de agente.")
    assert quote_in(edited) == "conéctalo ya por MCP"


def test_deleting_all_of_it_orphans_it() -> None:
    assert quote_in(TEXT.replace(QUOTE, "")) is None
    assert quote_in("Algo completamente distinto.") is None


def test_repeats_pick_the_nearest_and_json_round_trips() -> None:
    text = "MCP aquí. " * 3
    a = anchors.at(text, 10, 13)
    moved = anchors.relocate(text, a)
    assert moved is not None and moved.offset == 10
    data = a.as_json()
    assert data["yjs"] is None and anchors.Anchor.from_json(data) == a
    assert anchors.first(text, "") is None and anchors.first(text, "nada") is None
