"""The visual blocks of Folio 3.3 and 3.4: what the schema accepts and how Markdown writes
and reads them."""

import pytest

from radicle.folio.services import convert, schema
from radicle.folio.services.parse_markdown import from_markdown
from tests.unit.folio_docs import block


def doc(*blocks: dict) -> dict:
    return {"type": "doc", "content": list(blocks)}


VISUAL = {"format": "svg", "code": "<svg></svg>", "description": "Un dibujo"}


@pytest.mark.parametrize(
    ("node", "says"),
    [
        (block("visual", **(VISUAL | {"description": "  "})), "needs a description"),
        (block("visual", **(VISUAL | {"format": "pdf"})), "must be one of svg, html"),
        (block("visual", **(VISUAL | {"code": "x" * 524_289})), "longer than 524288"),
        (block("chart", kind="bar", data=[["a", "b"]]), "header row and at least one"),
        (block("chart", kind="bar", data=[["a", "b"], ["x", "1"]]), "must be a number"),
        (block("chart", kind="bar", data=[["a", "b"], ["x", 1, 2]]), "every row has 2 cells"),
        (block("chart", kind="bar", data=[["a"], ["x"]]), "2 to 10 columns"),
        (block("chart", kind="donut", data=[["a", "b"], ["x", 1]]), "must be one of"),
        (block("timeline", items=[]), "1 to 100 items"),
        (block("timeline", items=[{"date": "hoy"}]), "with a title"),
        (block("timeline", items=[{"title": "x", "color": "red"}]), "with a title"),
        (block("diagram", language="plantuml", source="a"), "must be one of mermaid"),
        (block("formula"), "latex"),
        (block("comparison", block("comparisonSide", block("paragraph"))), "at least 2"),
        (block("pageList", label="x", limit=99), "at most 50"),
        (block("databaseView", database="inventario"), "a database's id"),
        (block("databaseView"), "database"),
    ],
)
def test_the_schema_says_what_is_wrong(node: dict, says: str) -> None:
    with pytest.raises(schema.SchemaError) as exc:
        schema.validate(doc(node))
    assert says in exc.value.detail


def test_valid_blocks_pass() -> None:
    nodes = [
        block("visual", **VISUAL),
        block("chart", kind="pie", data=[["Estado", "Tickets"], ["Abierto", 4], ["Cerrado", 1.5]]),
        block("timeline", items=[{"date": "Q1", "title": "Beta"}]),
        block("formula", latex="\\sum_i x_i"),
        block("pageList", label="onboarding"),
        block("databaseView", database="6f1c3a52-9d2e-4b8a-a1f0-3c5e7d9b2a14"),
    ]
    assert schema.validate(doc(*nodes)) == doc(*nodes)


def test_markdown_round_trip_of_a_visual_with_backticks() -> None:
    code = "<div>```no rompe```</div>"
    visual = block("visual", format="html", code=code, description='Con comillas "y" ticks')
    md = convert.to_markdown(doc(visual))
    assert md.startswith("````visual")
    assert from_markdown(md) == doc(visual)


@pytest.mark.parametrize(
    "fence",
    [
        "```chart\n| solo encabezado |\n```",
        "```visual{format=svg}\n<svg/>\n```",  # no description
        "```timeline\n\n```",
        "```mermaid\n```",
    ],
)
def test_fences_that_make_no_block_stay_code(fence: str) -> None:
    parsed = from_markdown(fence)
    assert parsed["content"][0]["type"] == "codeBlock"


def test_markdown_written_by_hand() -> None:
    md = (
        "```chart{kind=line title=Ventas}\n| Mes | Ventas |\n|---|---|\n| Ene | 1,200 |\n"
        "| Feb | 3.5 |\n| Mar | n/a |\n```\n\n"
        "```timeline\nSolo un hito\n2026-12 | Lanzamiento | Público\n```\n\n"
        "::pages{label=#Onboarding limit=900}\n\n"
        ":::side{title=suelto}\nfuera de compare\n:::"
    )
    chart, timeline, pages, loose = from_markdown(md)["content"]
    assert chart["attrs"] == {
        "kind": "line",
        "title": "Ventas",
        "data": [["Mes", "Ventas"], ["Ene", 1200], ["Feb", 3.5], ["Mar", 0]],
    }
    assert timeline["attrs"]["items"] == [
        {"title": "Solo un hito"},
        {"date": "2026-12", "title": "Lanzamiento", "text": "Público"},
    ]
    assert pages["attrs"] == {"label": "onboarding", "limit": 50}
    assert loose["type"] == "paragraph"  # a side only means something inside compare
