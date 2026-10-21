"""A Folio document with every phase 1 block, shared by schema and converter tests."""

from typing import Any


def t(text: str, *marks: str, **attrs: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = [{"type": m, **({"attrs": attrs} if m == "link" else {})} for m in marks]
    return node


def p(*children: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(children)}


def block(node_type: str, /, *children: dict[str, Any], **attrs: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"type": node_type}
    if attrs:
        node["attrs"] = attrs
    if children:
        node["content"] = list(children)
    return node


EVERY_BLOCK: dict[str, Any] = {
    "type": "doc",
    "content": [
        block("heading", t("Conecta un agente"), level=1),
        p(
            t("Texto "),
            t("negrita", "bold"),
            t(" y "),
            t("código", "code"),
            t(" con "),
            t("link", "link", href="https://radicle.dev"),
            {"type": "hardBreak"},
            {"type": "mention", "attrs": {"handle": "fernando"}},
            t(" "),
            {"type": "status", "attrs": {"text": "Listo", "color": "green"}},
        ),
        block("heading", t("Antes de empezar"), level=2),
        block("bulletList", block("listItem", p(t("uno"))), block("listItem", p(t("dos")))),
        block("orderedList", block("listItem", p(t("primero"))), start=1),
        block(
            "taskList",
            block("taskItem", p(t("hecho")), checked=True),
            block("taskItem", p(t("pendiente")), checked=False),
        ),
        block("blockquote", p(t("Una cita"))),
        block("codeBlock", t("print('hola')"), language="python"),
        block(
            "table",
            block(
                "tableRow", block("tableHeader", p(t("Campo"))), block("tableHeader", p(t("Regla")))
            ),
            block(
                "tableRow",
                block("tableCell", p(t("Título"))),
                block("tableCell", p(t("1 a 200")), background="#ECF8C8"),
            ),
        ),
        block("panel", p(t("Ojo con el token.")), kind="warning"),
        block("expand", p(t("Detalles")), title="Más"),
        block(
            "columns",
            block("column", p(t("izquierda"))),
            block("column", p(t("derecha"))),
            layout="two",
        ),
        block("tableOfContents"),
        block("childPages"),
        block(
            "image",
            src="/api/v1/folio/assets/1",
            alt="Diagrama",
            caption="El flujo",
            size="large",
            align="center",
        ),
        block("file", assetId="a1", name="spec.pdf", mimeType="application/pdf", size=1024),
        block("video", src="https://example.com/v.mp4", caption="Demo"),
        block(
            "visual",
            format="svg",
            code=(
                '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="var(--accent)"/></svg>'
            ),
            title="Raíz",
            description="Un círculo lima: la semilla de Radicle.",
        ),
        block("diagram", language="mermaid", source="graph TD\n  A-->B", caption="Flujo"),
        block(
            "chart",
            kind="bar",
            title="Tickets por área",
            data=[["Área", "Abiertos", "Cerrados"], ["Legal", 3, 5], ["Backend", 7, 2.5]],
        ),
        block(
            "timeline",
            items=[
                {"date": "2026-11-01", "title": "Beta", "text": "Equipo interno"},
                {"title": "Lanzamiento"},
            ],
        ),
        block("formula", latex="E = mc^2"),
        block(
            "comparison",
            block("comparisonSide", p(t("rápido")), title="Antes"),
            block("comparisonSide", p(t("más rápido"))),
        ),
        block("pageList", label="onboarding", limit=5, space="docs"),
        block("horizontalRule"),
        p(t("Fin")),
    ],
}
