"""HTML to Folio Markdown, for imports (Folio 5.3)."""

from radicle.folio.services.importing.html_md import parse, to_markdown


def test_html_becomes_markdown() -> None:
    html = (
        "<h2>Título</h2><p>Uno <b>dos</b> <i>tres</i> <code>x_y</code><br>cuatro</p>"
        "<ul><li>a<ul><li>b</li></ul></li><li><p>c</p></li></ul>"
        "<blockquote><p>cita</p></blockquote><hr><pre>a &lt; b\n</pre>"
        "<table><tr><th>A</th><th>B|C</th></tr><tr><td>1</td></tr></table>"
        "<script>alert(1)</script><p><a href='#x'>ancla</a> <a href='mailto:a@b.c'>mail</a></p>"
    )
    md = to_markdown(parse(html), lambda target, label, image: None)
    assert md == (
        "## Título\n\nUno **dos** *tres* `x_y`  \ncuatro\n\n- a\n  - b\n- c\n\n> cita\n\n---\n\n"
        "```\na < b\n```\n\n| A | B\\|C |\n| --- | --- |\n| 1 |   |\n\nancla [mail](mailto:a@b.c)\n"
    )
