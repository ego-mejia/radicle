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
        (block("whiteboard", whiteboard="mapa"), "a whiteboard's id"),
        (block("calendar", calendar="releases"), "a calendar's id"),
        (block("calendar", calendar="5d2f8a17-3c4b-4e6a-9f1d-2b7c8e9a0f13", view="year"), "month"),
        (block("chart", kind="bar"), "header row"),
        (block("chart", kind="bar", source="table", data=[["a", "b"], ["x", 1]]), "has no data"),
        (block("chart", kind="bar", source="sheet"), "must be one of table"),
        (block("timeline", items=[{"title": "x", "status": "late"}]), "is one of done"),
        (block("pageList", label="x", order="random"), "must be one of newest, title"),
        (block("paragraph", {"type": "inlineFormula"}), "latex"),
        (block("paragraph", {"type": "ticket", "attrs": {"key": "pa-4"}}), "like PA-4"),
        (block("ticketTable", rql="project = PA", limit=500), "at most 100"),
        (block("ticketTable"), "rql"),
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
        block("whiteboard", whiteboard="0b7e2c41-5a3d-4f6e-9c8b-1d2e3f4a5b6c"),
        block("calendar", calendar="5d2f8a17-3c4b-4e6a-9f1d-2b7c8e9a0f13"),
    ]
    assert schema.validate(doc(*nodes)) == doc(*nodes)


def test_ticket_keys_in_markdown_and_text() -> None:
    parsed = from_markdown("Ver :ticket[pa-4] y `:ticket[PA-5]`.")
    assert parsed["content"][0]["content"][1] == {"type": "ticket", "attrs": {"key": "PA-4"}}
    assert convert.to_text(parsed) == "Ver PA-4 y :ticket[PA-5]."


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


def _round_trip(*nodes: dict) -> None:
    md = convert.to_markdown(doc(*nodes))
    assert from_markdown(md) == doc(*nodes), md


def test_options_round_trip() -> None:
    _round_trip(
        block("table", block("tableRow", block("tableHeader", block("paragraph")))),
        block("chart", kind="line", title="Del cuadro", source="table"),
        block(
            "timeline",
            items=[
                {"date": "Q1", "title": "Beta", "status": "done"},
                {"title": "GA", "status": "in_progress", "text": "En curso"},
                {"date": "Q3", "title": "2.0", "status": "planned"},
                {"title": "Sin estado"},
            ],
        ),
        block("pageList", label="onboarding", order="title", limit=5),
    )
    formula = {"type": "inlineFormula", "attrs": {"latex": "a`b + x^2"}}
    _round_trip(
        block(
            "paragraph",
            {"type": "text", "text": "Vale "},
            formula,
            {"type": "text", "text": " hoy."},
        )
    )
    _round_trip(block("paragraph", {"type": "inlineFormula", "attrs": {"latex": "\\frac{1}{2}"}}))


def test_inline_math_only_between_dollars() -> None:
    para = from_markdown("Cuesta $5 y `code`, y $`e=mc^2`$.")["content"][0]["content"]
    assert [n["type"] for n in para] == ["text", "text", "text", "inlineFormula", "text"]
    assert para[3]["attrs"]["latex"] == "e=mc^2" and para[4]["text"] == "."
    assert "e=mc^2" in convert.to_text(doc(block("paragraph", para[3])))


def test_ticket_progress_round_trips_with_or_without_title() -> None:
    from radicle.folio.services import convert
    from radicle.folio.services.parse_markdown import from_markdown

    for md, attrs in (("::progress{}", {}), ("::progress{title=Avance}", {"title": "Avance"})):
        doc = from_markdown(md)
        assert doc["content"] == [{"type": "ticketProgress", "attrs": attrs}]
        assert convert.to_markdown(doc).strip() == md
