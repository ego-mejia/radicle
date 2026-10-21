"""TipTap JSON in and out of Yjs (Folio 2.2): the shape y-prosemirror writes."""

import copy

import pycrdt

from radicle.folio.services import schema, ydoc
from tests.unit.folio_docs import EVERY_BLOCK, block, p, t


def test_every_block_survives_the_round_trip() -> None:
    doc = ydoc.from_json(EVERY_BLOCK)
    assert ydoc.to_json(doc) == schema.validate(copy.deepcopy(EVERY_BLOCK))


def test_text_shares_one_xml_text_and_marks_are_formats() -> None:
    doc = ydoc.from_json({"type": "doc", "content": [p(t("Hola "), t("mundo", "bold"))]})
    paragraph = next(iter(ydoc.fragment(doc).children))
    texts = list(paragraph.children)
    assert len(texts) == 1 and isinstance(texts[0], pycrdt.XmlText)
    assert texts[0].diff() == [("Hola ", None), ("mundo", {"bold": {}})]


def test_what_the_browser_adds_is_dropped() -> None:
    doc = pycrdt.Doc()
    frag = ydoc.fragment(doc)
    heading = frag.children.append(pycrdt.XmlElement("heading", {"level": 2, "textAlign": "left"}))
    text = heading.children.append(pycrdt.XmlText())
    text.insert(0, "Hola", {"bold": {}, "highlight": {"color": "red"}})
    frag.children.append(pycrdt.XmlElement("unknownWidget", {}))
    cell = frag.children.append(pycrdt.XmlElement("image", {"src": "/a.png", "alt": None}))
    assert cell is not None
    assert ydoc.to_json(doc) == {
        "type": "doc",
        "content": [
            block("heading", t("Hola", "bold"), level=2),
            {"type": "image", "attrs": {"src": "/a.png"}},
        ],
    }
    schema.validate(ydoc.to_json(doc))


def test_append_keeps_what_others_wrote() -> None:
    server = ydoc.from_json({"type": "doc", "content": [p(t("uno"))]})
    client = pycrdt.Doc()
    client.apply_update(server.get_update())
    ydoc.fragment(client).children.append(pycrdt.XmlElement("paragraph", {})).children.append(
        pycrdt.XmlText("dos")
    )
    ydoc.append(ydoc.fragment(server), [p(t("tres"))])
    client.apply_update(server.get_update(client.get_state()))
    server.apply_update(client.get_update(server.get_state()))
    texts = [n["content"][0]["text"] for n in ydoc.to_json(server)["content"]]
    assert sorted(texts) == ["dos", "tres", "uno"] and texts[0] == "uno"
    assert ydoc.to_json(server) == ydoc.to_json(client)


def test_write_replaces_and_numbers_come_back_as_ints() -> None:
    doc = ydoc.from_json({"type": "doc", "content": [p(t("viejo"))]})
    ydoc.write(
        ydoc.fragment(doc),
        {"type": "doc", "content": [block("orderedList", block("listItem", p(t("a"))), start=3)]},
    )
    out = ydoc.to_json(doc)
    assert out["content"][0]["attrs"] == {"start": 3}
    assert isinstance(out["content"][0]["attrs"]["start"], int)


def test_clean_leaves_out_blocks_that_are_not_set_up() -> None:
    doc = {
        "type": "doc",
        "content": [
            {"type": "databaseView", "attrs": {"database": None}},
            {"type": "visual", "attrs": {"format": "svg", "code": "<svg/>"}},
            {"type": "paragraph"},
        ],
    }
    assert ydoc.clean(doc) == {"type": "doc", "content": [{"type": "paragraph"}]}
