"""Checking visuals and adding blocks under a heading (Folio 3.3 and 3.4)."""

import pytest

from radicle.folio.services import chunking, visuals
from radicle.platform.errors import ValidationFailed

GOOD = '<svg xmlns="http://www.w3.org/2000/svg"><text fill="var(--rdc-text)">Hola</text></svg>'
DESC = "Un saludo en el color del texto."


def test_a_good_visual_passes() -> None:
    report = visuals.check("svg", GOOD, DESC)
    assert report.valid and not report.warnings  # the xmlns URL is not a request


@pytest.mark.parametrize(
    ("fmt", "code", "problem"),
    [
        ("svg", "<div>x</div>", "starts with <svg>"),
        ("html", "", "code is empty"),
        ("html", "é" * 262_145, "the limit is 512 KB"),
        ("gif", GOOD, "format is svg or html"),
        ("html", "<script>new XMLHttpRequest()</script>", "XMLHttpRequest"),
        ("html", "<script>new WebSocket('wss://x')</script>", "WebSocket"),
        ("html", "<script>import('x')</script>", "import()"),
        ("html", '<script src="https://cdn.x/lib.js"></script>', "https://cdn.x/lib.js"),
        ("html", "<style>@import 'a.css'</style>", "@import"),
        ("html", "<div style=\"background:url('//x.io/a.png')\"></div>", "//x.io/a.png"),
        ("html", "<script>top.location='x'</script>", "can't reach the page"),
        ("html", "<script>window.parent.document</script>", "can't reach the page"),
        ("html", '<meta http-equiv="Content-Security-Policy" content="x">', "meta http-equiv"),
        ("html", "<p style='color:var(--rdc-pink)'>x</p>", "not a Radicle token"),
    ],
)
def test_problems(fmt: str, code: str, problem: str) -> None:
    report = visuals.check(fmt, code, DESC)
    assert not report.valid
    assert any(problem in p for p in report.problems), report.problems


def test_title_is_needed_to_publish() -> None:
    assert "title is required" in visuals.check("svg", GOOD, DESC, title=" ").problems[0]
    titled = {"type": "visual", "attrs": {"format": "svg", "code": GOOD, "title": "Hola"}}
    untitled = {"type": "visual", "attrs": {"format": "svg", "code": GOOD}}
    nested = {"type": "panel", "content": [untitled]}
    visuals.require_publishable({"type": "doc", "content": [titled]})
    with pytest.raises(ValidationFailed, match=r"visual 2, 3 has none"):
        visuals.require_publishable({"type": "doc", "content": [titled, untitled, nested]})


def test_description_and_token_warnings() -> None:
    assert "description is required" in visuals.check("svg", GOOD, "  ").problems[0]
    report = visuals.check("svg", '<svg><rect fill="#ff0000"/></svg>', "Corto")
    assert report.valid and len(report.warnings) == 2
    report = visuals.check("svg", '<svg fill="var(--rdc-text)" stroke="#000"/>', DESC)
    assert "fixed (#hex)" in report.warnings[0]
    # Inline images are fine.
    assert visuals.check("html", '<img src="data:image/png;base64,AA">', DESC).problems == []


def _h(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _p(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


DOC = {"type": "doc", "content": [_h(1, "Uno"), _p("a"), _h(2, "Sub"), _p("b"), _h(1, "Dos")]}
FORMULA = {"type": "formula", "attrs": {"latex": "x^2"}}


def test_insert_at_the_end_of_a_section() -> None:
    types = lambda d: [n["type"] for n in d["content"]]  # noqa: E731
    out = visuals.insert(DOC, FORMULA, "uno")
    assert types(out)[4] == "formula"  # after the subsection, before "Dos"
    out = visuals.insert(DOC, FORMULA, "## Sub")
    assert types(out)[4] == "formula"
    assert types(visuals.insert(DOC, FORMULA))[-1] == "formula"
    assert types(visuals.insert(DOC, FORMULA, "Dos"))[-1] == "formula"
    assert DOC["content"][-1]["type"] == "heading"  # the input is not changed


def test_insert_errors() -> None:
    with pytest.raises(ValidationFailed, match="Headings: Uno, Sub, Dos"):
        visuals.insert(DOC, FORMULA, "Tres")
    with pytest.raises(ValidationFailed, match="It has no headings"):
        visuals.insert({"type": "doc", "content": []}, FORMULA, "Tres")
    with pytest.raises(ValidationFailed, match="needs the network"):
        bad = {"format": "html", "code": "<script>fetch('/x')</script>", "description": "x"}
        visuals.insert(DOC, {"type": "visual", "attrs": bad})
    with pytest.raises(ValidationFailed, match="latex"):
        visuals.insert(DOC, {"type": "formula", "attrs": {}})


def test_chunks_read_descriptions_not_code() -> None:
    visual = {"type": "visual", "attrs": {"format": "svg", "code": GOOD, "description": DESC}}
    pages = {"type": "pageList", "attrs": {"label": "mcp"}}
    doc = {"type": "doc", "content": [_h(1, "Uno"), visual, pages, _p("fin")]}
    text = chunking.chunk(doc)[0].text
    assert DESC in text and "<svg" not in text and "mcp" not in text and "fin" in text
