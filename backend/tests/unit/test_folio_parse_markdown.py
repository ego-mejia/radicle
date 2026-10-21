"""Markdown to Folio documents (Folio 1.2), and the round trip with `convert`."""

import copy
from pathlib import Path

import pytest

from radicle.folio.services import convert
from radicle.folio.services.parse_markdown import from_markdown
from tests.unit.folio_docs import EVERY_BLOCK

EXPECTED_MD = (Path(__file__).parent / "folio_every_block.md").read_text()


def _without_cell_colors(doc: dict) -> dict:
    """What Markdown cannot keep (docs/folio/markdown.md): cell spans, widths and colors."""
    doc = copy.deepcopy(doc)

    def walk(node: dict) -> None:
        if node["type"] in ("tableCell", "tableHeader"):
            node.pop("attrs", None)
        for child in node.get("content", []):
            walk(child)

    walk(doc)
    return doc


def test_round_trip_of_every_block() -> None:
    assert from_markdown(convert.to_markdown(EVERY_BLOCK)) == _without_cell_colors(EVERY_BLOCK)


@pytest.mark.parametrize("index", range(len(EVERY_BLOCK["content"])))
def test_round_trip_block_by_block(index: int) -> None:
    doc = {"type": "doc", "content": [EVERY_BLOCK["content"][index]]}
    assert from_markdown(convert.to_markdown(doc)) == _without_cell_colors(doc)


def test_markdown_is_stable() -> None:
    assert convert.to_markdown(from_markdown(EXPECTED_MD)) == EXPECTED_MD
    assert from_markdown("") == {"type": "doc", "content": []}


def test_what_agents_usually_write() -> None:
    doc = from_markdown(
        "##### Deep heading\n\n"
        "Intro with *emphasis*, a [link](https://x.dev) and <b>html</b>.\n\n"
        "* one\n* two\n  1. nested\n\n"
        "Then:\n\n"
        "    indented code\n\n"
        "1. [ ] not a task in an ordered list\n"
    )
    heading, intro, bullets, _, code, ordered = doc["content"]
    assert heading["attrs"] == {"level": 4}
    assert intro["content"][-1] == {"type": "text", "text": " and <b>html</b>."}
    assert bullets["content"][1]["content"][1]["type"] == "orderedList"
    assert code == {
        "type": "codeBlock",
        "attrs": {"language": None},
        "content": [{"type": "text", "text": "indented code"}],
    }
    assert ordered["type"] == "orderedList"


def test_directives_inside_code_stay_code() -> None:
    doc = from_markdown("```md\n:::panel{kind=tip}\n[[toc]]\n:::\n```\n")
    assert [b["type"] for b in doc["content"]] == ["codeBlock"]
    assert doc["content"][0]["content"][0]["text"] == ":::panel{kind=tip}\n[[toc]]\n:::"


def test_odd_directives_degrade_to_their_content() -> None:
    doc = from_markdown(":::panel{kind=danger}\nx\n:::\n\n:::column\nloose\n:::\n\n:::expand\nopen")
    panel, loose, expand = doc["content"]
    assert panel["attrs"] == {"kind": "info"}
    assert loose == {"type": "paragraph", "content": [{"type": "text", "text": "loose"}]}
    assert expand["type"] == "expand" and "attrs" not in expand
    single = from_markdown("::::columns{layout=two}\n:::column\nsolo\n:::\n::::")
    assert single["content"][0]["type"] == "paragraph"


def test_mentions_status_and_underline() -> None:
    [paragraph] = from_markdown(
        "Hi @ana, mail a@b.co, :status[Blocked]{color=red} :u[**under**] `@code`"
    )["content"]
    kinds = [(n["type"], n.get("text") or n.get("attrs")) for n in paragraph["content"]]
    assert ("mention", {"handle": "ana"}) in kinds
    assert ("status", {"text": "Blocked", "color": "red"}) in kinds
    assert not any(k == "mention" and v == {"handle": "b"} for k, v in kinds)
    bold_under = next(n for n in paragraph["content"] if n.get("text") == "under")
    assert [m["type"] for m in bold_under["marks"]] == ["bold", "underline"]
    code = next(n for n in paragraph["content"] if n.get("text") == "@code")
    assert code["marks"] == [{"type": "code"}]
