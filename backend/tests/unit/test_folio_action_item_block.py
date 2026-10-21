"""The action item block (Folio 2.4): schema, Markdown both ways and plain text."""

import pytest

from radicle.folio.services import convert, schema
from radicle.folio.services.parse_markdown import from_markdown

ITEM = {
    "type": "actionItem",
    "attrs": {"id": "ai-1", "done": False, "assignee": "ana", "due": "2026-11-01"},
    "content": [
        {"type": "text", "text": "Revisar el "},
        {"type": "text", "text": "deploy", "marks": [{"type": "bold"}]},
    ],
}
DOC = {"type": "doc", "content": [ITEM]}


def test_it_validates_and_needs_an_id() -> None:
    assert schema.validate(DOC)["content"][0]["attrs"]["id"] == "ai-1"
    no_id = {"type": "doc", "content": [{"type": "actionItem", "attrs": {"done": True}}]}
    with pytest.raises(schema.SchemaError):
        schema.validate(no_id)


def test_markdown_round_trip() -> None:
    md = convert.to_markdown(DOC)
    assert md == "::task[Revisar el **deploy**]{id=ai-1 assignee=ana due=2026-11-01}\n"
    assert from_markdown(md) == DOC
    done = {"type": "doc", "content": [ITEM | {"attrs": ITEM["attrs"] | {"done": True}}]}
    assert from_markdown(convert.to_markdown(done)) == done
    assert convert.to_text(DOC) == "Revisar el deploy"


def test_agents_can_write_it_without_an_id_or_with_a_bad_date() -> None:
    doc = from_markdown("::task[Llamar a @luis]{assignee=@Ana due=mañana}")
    item = doc["content"][0]
    assert item["attrs"]["id"].startswith("ai-") and item["attrs"]["assignee"] == "ana"
    assert item["attrs"]["due"] is None and item["attrs"]["done"] is False
    assert item["content"][1] == {"type": "mention", "attrs": {"handle": "luis"}}
    # Inside a fenced code block it stays code.
    code = from_markdown("```\n::task[no]{id=x}\n```")
    assert code["content"][0]["type"] == "codeBlock"
