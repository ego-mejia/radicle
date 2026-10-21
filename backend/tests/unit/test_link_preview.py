"""Link previews: which providers embed and how a page's tags become a card (Folio 3.7)."""

import pytest

from radicle.folio.services.link_preview import embed_for, parse


@pytest.mark.parametrize(
    ("url", "provider", "embed"),
    [
        (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        ),
        (
            "https://youtu.be/dQw4w9WgXcQ?t=3",
            "youtube",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        ),
        (
            "https://www.figma.com/design/abc/Mi-diseno",
            "figma",
            "https://www.figma.com/embed?embed_host=radicle&url=https%3A%2F%2Fwww.figma.com%2Fdesign%2Fabc%2FMi-diseno",
        ),
        (
            "https://www.loom.com/share/0123456789abcdef0123456789abcdef",
            "loom",
            "https://www.loom.com/embed/0123456789abcdef0123456789abcdef",
        ),
        (
            "https://docs.google.com/document/d/1AbC_d-E/edit",
            "google_docs",
            "https://docs.google.com/document/d/1AbC_d-E/preview",
        ),
        (
            "https://gist.github.com/ana/0123456789abcdef0123",
            "github",
            "https://gist.github.com/ana/0123456789abcdef0123.pibb",
        ),
        ("https://github.com/ego-mejia/radicle", None, None),
        ("https://www.youtube.com/watch?v=<script>", None, None),
        ("https://example.com/figma.com/design/x", None, None),
    ],
)
def test_embed_for(url: str, provider: str | None, embed: str | None) -> None:
    assert embed_for(url) == (provider, embed)


def test_parse_reads_open_graph_then_falls_back() -> None:
    html = """<html><head><title> Título viejo </title>
      <meta property="og:title" content="Radicle Folio">
      <meta name="description" content="Docs para personas y agentes.">
      <meta property="og:image" content="/cover.png">
      <link rel="shortcut icon" href="/favicon.svg"></head></html>"""
    p = parse("https://radicle.example.com/folio", html)
    assert (p.title, p.description, p.site_name) == (
        "Radicle Folio",
        "Docs para personas y agentes.",
        "radicle.example.com",
    )
    assert p.image_url == "https://radicle.example.com/cover.png"
    assert p.icon_url == "https://radicle.example.com/favicon.svg"
    bare = parse("https://example.com/x", "<title>Solo título</title>")
    assert bare.title == "Solo título" and bare.icon_url == "https://example.com/favicon.ico"
    assert parse("https://example.com/x", "").title == "https://example.com/x"
