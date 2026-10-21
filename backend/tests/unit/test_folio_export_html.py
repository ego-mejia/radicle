"""Folio documents as static HTML for exports: every block, escaped and sandboxed."""

from radicle.folio.services.exporting.html_render import Links, render
from tests.unit.folio_docs import EVERY_BLOCK


def _links() -> Links:
    return Links(asset=lambda i: f"assets/{i}.bin", children=[("Hija", "hija.html")])


def test_every_block_renders() -> None:
    html = render(EVERY_BLOCK, _links())
    assert html.startswith("<") and "<table>" in html and "<details>" in html
    assert 'sandbox="allow-scripts"' in html and "allow-same-origin" not in html


def test_text_is_escaped_and_links_are_checked() -> None:
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "<script>x</script>"},
                    {
                        "type": "text",
                        "text": "mal",
                        "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
                    },
                    {"type": "text", "text": "bien", "marks": [{"type": "bold"}]},
                ],
            }
        ],
    }
    html = render(doc, _links())
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "javascript:" not in html and "<strong>bien</strong>" in html


def test_live_blocks_toc_children_and_charts_from_the_table_above() -> None:
    table = {
        "type": "table",
        "content": [
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableHeader",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Mes"}]}
                        ],
                    },
                    {
                        "type": "tableHeader",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Usuarios"}]}
                        ],
                    },
                ],
            },
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableCell",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Oct"}]}
                        ],
                    },
                    {
                        "type": "tableCell",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "12"}]}
                        ],
                    },
                ],
            },
        ],
    }
    doc = {
        "type": "doc",
        "content": [
            {"type": "tableOfContents"},
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Uso"}],
            },
            table,
            {"type": "chart", "attrs": {"kind": "bar", "source": "table"}},
            {"type": "ticketTable", "attrs": {"rql": "project = PA"}},
            {"type": "childPages"},
            {"type": "image", "attrs": {"assetId": "a1", "alt": "Mapa"}},
        ],
    }
    html = render(doc, _links())
    assert '<nav class="toc"><ul><li class="h2"><a href="#s1">Uso</a></li></ul></nav>' in html
    assert html.count("<td>Oct</td>") == 1  # the chart's own table
    assert "Live content from Radicle" in html
    assert '<a href="hija.html">Hija</a>' in html and 'src="assets/a1.bin"' in html
