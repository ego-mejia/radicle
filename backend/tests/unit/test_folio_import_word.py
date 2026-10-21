"""Word documents into pages (Folio 5.3). The .docx is built here the way Word writes one."""

import io
import zipfile

from radicle.folio.services.importing.word import read_word

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
PNG = b"\x89PNG\r\n\x1a\n" + b"2" * 16


def p(text: str, style: str | None = None, num: tuple[str, str] | None = None) -> str:
    props = ""
    if style:
        props += f'<w:pStyle w:val="{style}"/>'
    if num:
        props += f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>'
    return f"<w:p><w:pPr>{props}</w:pPr><w:r><w:t xml:space='preserve'>{text}</w:t></w:r></w:p>"


BODY = (
    p("Guía de despliegue", "Title")
    + p("Antes de empezar", "Heading1")
    + "<w:p><w:r><w:t xml:space='preserve'>Usa </w:t></w:r>"
    "<w:r><w:rPr><w:b/></w:rPr><w:t>Docker</w:t></w:r>"
    "<w:r><w:rPr><w:i/><w:b w:val='0'/></w:rPr><w:t xml:space='preserve'> siempre </w:t></w:r>"
    "<w:hyperlink r:id='rIdLink'><w:r><w:t>la guía</w:t></w:r></w:hyperlink></w:p>"
    + p("Instalar", num=("1", "0"))
    + p("Configurar", num=("1", "0"))
    + p("Con token", num=("2", "1"))
    + "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Variable</w:t></w:r></w:p></w:tc>"
    "<w:tc><w:p><w:r><w:t>Valor</w:t></w:r></w:p></w:tc></w:tr>"
    "<w:tr><w:tc><w:p><w:r><w:t>PORT</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
    "<w:p><w:r><w:drawing><a:graphic><a:graphicData><a:blip r:embed='rIdImg'/>"
    "</a:graphicData></a:graphic></w:drawing></w:r></w:p>" + p("Detalles", "Ttulo2")
)
NUMBERING = (
    f"<w:numbering {W}>"
    "<w:abstractNum w:abstractNumId='10'><w:lvl w:ilvl='0'><w:numFmt w:val='decimal'/></w:lvl>"
    "</w:abstractNum><w:abstractNum w:abstractNumId='11'><w:lvl w:ilvl='1'>"
    "<w:numFmt w:val='bullet'/></w:lvl></w:abstractNum>"
    "<w:num w:numId='1'><w:abstractNumId w:val='10'/></w:num>"
    "<w:num w:numId='2'><w:abstractNumId w:val='11'/></w:num></w:numbering>"
)


def docx(body: str = BODY, core: bool = True) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(
            "word/document.xml", f"<w:document {W} {R} {A}><w:body>{body}</w:body></w:document>"
        )
        z.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdLink" Target="https://radicle.dev/docs" TargetMode="External"/>'
            '<Relationship Id="rIdImg" Target="media/image1.png"/></Relationships>',
        )
        z.writestr(
            "word/styles.xml",
            f"<w:styles {W}><w:style w:styleId='Ttulo2'><w:name w:val='heading 2'/></w:style>"
            "</w:styles>",
        )
        z.writestr("word/numbering.xml", NUMBERING)
        z.writestr("word/media/image1.png", PNG)
        if core:
            z.writestr(
                "docProps/core.xml",
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
                'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
                "<dc:creator>luis@example.com</dc:creator><cp:keywords>deploy; Docker</cp:keywords>"
                "</cp:coreProperties>",
            )
    return out.getvalue()


def test_a_document_becomes_a_page() -> None:
    bundle = read_word({"Despliegue.docx": docx()})
    page = bundle.pages[0]
    assert page.title == "Guía de despliegue"
    assert page.author == "luis@example.com" and page.labels == ["deploy", "docker"]
    assert page.markdown == (
        "# Antes de empezar\n\nUsa **Docker** *siempre* [la guía](https://radicle.dev/docs)\n\n"
        "1. Instalar\n1. Configurar\n  - Con token\n\n"
        "| Variable | Valor |\n| --- | --- |\n| PORT |   |\n\n"
        "![image1.png](import:a1)\n\n## Detalles\n"
    )
    assert bundle.attachments["a1"].data == PNG


def test_folders_of_documents_and_broken_files() -> None:
    bundle = read_word(
        {"Ops/Runbooks/Reinicio.docx": docx(p("Reiniciar"), core=False), "Ops/x.docx": b"nope"}
    )
    assert [(p.title, p.kind, p.parent_id) for p in bundle.pages] == [
        ("Ops", "folder", None),
        ("Runbooks", "folder", "dir:Ops"),
        ("Reinicio", "page", "dir:Ops/Runbooks"),
        ("x", "page", "dir:Ops"),
    ]
    assert bundle.pages[2].markdown == "Reiniciar\n"
    assert bundle.pages[3].errors == ["This file is not a valid .docx. Save it again from Word."]
    assert read_word({"a.md": b"x"}).errors == [
        "No Word documents (.docx) were found in the upload."
    ]


def test_xml_with_entities_or_no_body_is_refused() -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("word/document.xml", '<!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>')
    page = read_word({"bomb.docx": out.getvalue()}).pages[0]
    assert page.errors == [
        "word/document.xml declares entities; it was not read.",
        "This .docx has no document body; is it a Word file?",
    ]
