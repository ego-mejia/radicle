"""Visual tools (Folio 3.3 and 3.4): an agent adds visuals, Mermaid diagrams, charts and
timelines to a draft, and checks a visual before it goes in. folio://guide/visuals has the
tokens, a starter and the sandbox rules."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.folio.mcp.read import NodeId
from radicle.folio.mcp.write import _explained
from radicle.folio.services import schema
from radicle.folio.services.visuals import CSP, MAX_HEIGHT, TOKENS
from radicle.platform.mcp.api import APIError, api

AfterHeading = Annotated[
    str | None,
    Field(description="Add it at the end of this section (heading text); the end if not"),
]

STARTER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" role="img">
  <style>
    .dot { animation: pulse 2s ease-in-out infinite; transform-origin: 60px 60px; }
    @keyframes pulse { 50% { transform: scale(1.15); } }
    @media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
  </style>
  <rect width="400" height="120" rx="10" fill="var(--rdc-surface)"
        stroke="var(--rdc-border)"/>
  <circle class="dot" cx="60" cy="60" r="28" fill="var(--rdc-accent-fill)"/>
  <text x="110" y="66" font-family="var(--rdc-font)" font-size="18"
        fill="var(--rdc-text)">Draft → Review → Published</text>
</svg>"""

GUIDE = f"""# Visuals in Folio

A visual is SVG or HTML that a page shows in a sandboxed iframe. Check it with
validate_visual, then add it with insert_visual under a heading of the draft.

## Sandbox rules

- No network. The page sets this policy, and anything outside the visual is blocked:
  `{CSP}`. Put the data in the code; images and fonts go as `data:` URLs.
- No page: it runs in an opaque origin (`sandbox="allow-scripts"`), so it can't read the
  page around it (`parent.document` throws), its cookies or its storage. Scripts run, but
  only inside the visual.
- Up to {schema.MAX_VISUAL // 1024} KB of code. The height follows the content, up to
  {MAX_HEIGHT} px.
- A title and a description are required to publish: the description is the alt text and
  what search and the assistant read.

## Theme

The page defines these CSS variables in the reader's theme and changes them live when the
reader switches between light and dark (`data-theme` on `<html>` says which). Use them
instead of fixed colors:

{chr(10).join(f"- `{t}`" for t in TOKENS)}

Respect `prefers-reduced-motion`: the page passes the reader's setting on.

## Starter

```svg
{STARTER}
```

## Other blocks

- insert_diagram: Mermaid source (flowchart, sequence, state, ER, gantt), in the theme.
- insert_chart: a table of numbers as a bar, line, area or pie chart.
- insert_timeline: dated milestones in order.

Prefer those over a hand-made visual when they fit: people can edit them in the editor.
"""


async def _add(ctx: Context, id: str, block: dict[str, Any], after: str | None) -> dict[str, Any]:
    async with api(ctx) as client:
        try:
            out = await client.call(
                "POST", f"/folio/nodes/{id}/blocks", json={"block": block, "after_heading": after}
            )
        except APIError as exc:
            raise _explained(exc) from exc
    return {"id": id, "content_md": out["content_md"]}


def register(server: MCPServer) -> None:
    @server.resource(
        "folio://guide/visuals",
        name="visuals-guide",
        title="Visuals guide",
        description="Tokens, a starter, the sandbox rules and the visual blocks",
        mime_type="text/markdown",
    )
    def guide() -> str:
        return GUIDE

    @server.tool()
    async def validate_visual(
        ctx: Context,
        format: Literal["svg", "html"],
        code: str,
        title: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Check a visual before inserting it: size, what the sandbox would block (network,
        the page around it), the Radicle tokens it uses, its title and its description."""
        body = {"format": format, "code": code, "title": title, "description": description}
        async with api(ctx) as client:
            out: dict[str, Any] = await client.call("POST", "/folio/visuals/check", json=body)
        return out

    @server.tool()
    async def insert_visual(
        ctx: Context,
        id: NodeId,
        format: Literal["svg", "html"],
        code: Annotated[str, Field(description="SVG or HTML; read folio://guide/visuals")],
        title: Annotated[str, Field(description="A few words; required to publish")],
        description: Annotated[str, Field(description="What it shows: alt text and search")],
        after_heading: AfterHeading = None,
    ) -> dict[str, Any]:
        """Add an SVG or HTML visual to the draft. It is checked like validate_visual and
        refused with the reasons when the sandbox would block it."""
        attrs = {"format": format, "code": code, "title": title, "description": description}
        return await _add(ctx, id, {"type": "visual", "attrs": attrs}, after_heading)

    @server.tool()
    async def insert_diagram(
        ctx: Context,
        id: NodeId,
        source: Annotated[str, Field(description="Mermaid source, e.g. 'flowchart LR; A-->B'")],
        caption: str | None = None,
        after_heading: AfterHeading = None,
    ) -> dict[str, Any]:
        """Add a Mermaid diagram to the draft; pages draw it in the reader's theme."""
        attrs = {"language": "mermaid", "source": source, "caption": caption}
        return await _add(ctx, id, {"type": "diagram", "attrs": attrs}, after_heading)

    @server.tool()
    async def insert_chart(
        ctx: Context,
        id: NodeId,
        kind: Literal["bar", "line", "area", "pie"],
        data: Annotated[
            list[list[str | int | float]],
            Field(
                description="Rows: the first names the columns ['Month', 'Open', 'Closed'], "
                "the others a label and numbers ['Jan', 4, 9]"
            ),
        ],
        title: str | None = None,
        after_heading: AfterHeading = None,
    ) -> dict[str, Any]:
        """Add a chart from a table of numbers to the draft."""
        attrs = {"kind": kind, "title": title, "data": data}
        return await _add(ctx, id, {"type": "chart", "attrs": attrs}, after_heading)

    @server.tool()
    async def insert_timeline(
        ctx: Context,
        id: NodeId,
        items: Annotated[
            list[dict[str, str]],
            Field(
                description="In order: {date, title, text, status}; title is required, "
                "status is done, in_progress or planned"
            ),
        ],
        after_heading: AfterHeading = None,
    ) -> dict[str, Any]:
        """Add a timeline of dated milestones to the draft."""
        return await _add(ctx, id, {"type": "timeline", "attrs": {"items": items}}, after_heading)
