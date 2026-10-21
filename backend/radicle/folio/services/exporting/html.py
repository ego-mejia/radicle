"""HTML export: a static site that opens from disk. One page per file in its folders, an
index for a space, the files under assets/ and one stylesheet."""

import io
import zipfile
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioSpace
from radicle.folio.services.exporting.html_render import Links, render
from radicle.folio.services.exporting.markdown import unique
from radicle.folio.services.exporting.pages import ExportPage, load_assets

STYLE = """
:root { color-scheme: light dark; --text: #1f2328; --muted: #6b7280; --line: #e5e7eb;
  --soft: #f6f7f9; --accent: #4d7c0f; }
@media (prefers-color-scheme: dark) { :root { --text: #e6e8eb; --muted: #9aa3ad;
  --line: #2b3138; --soft: #161b21; --accent: #a3e635; } body { background: #0d1117; } }
body { margin: 0; font: 16px/1.65 system-ui, sans-serif; color: var(--text); }
main { max-width: 760px; margin: 0 auto; padding: 32px 20px 80px; }
a { color: var(--accent); } img, video { max-width: 100%; }
.back { font-size: 14px; } .lead { color: var(--muted); font-size: 19px; }
pre { background: var(--soft); padding: 12px; overflow: auto; border-radius: 8px; }
table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid var(--line);
  padding: 6px 10px; text-align: left; vertical-align: top; }
blockquote { border-left: 3px solid var(--line); margin: 0; padding-left: 16px; }
.panel { border: 1px solid var(--line); background: var(--soft); padding: 4px 16px;
  border-radius: 8px; } .columns { display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.visual iframe { width: 100%; height: 420px; border: 1px solid var(--line); border-radius: 8px; }
figcaption, .live { color: var(--muted); font-size: 14px; }
.mention, .ticket, .status { background: var(--soft); padding: 0 4px; border-radius: 4px; }
ul.tree { list-style: none; padding-left: 0; } ul.tree ul { list-style: none; }
"""


def _doc(title: str, prefix: str, body: str) -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(title)}</title><link rel="stylesheet" href="{prefix}style.css">'
        f"</head><body><main>{body}</main></body></html>"
    )


async def write(
    db: AsyncSession, space: FolioSpace, pages: list[ExportPage], single: bool
) -> bytes:
    assets = await load_assets(db, pages)
    used: set[str] = set()
    files = {
        p.node.id: "index.html"
        if single
        else unique("/".join((*p.path, p.node.slug)), ".html", used)
        for p in pages
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("style.css", STYLE)
        for page in pages:
            prefix = "../" * page.depth

            def asset(asset_id: str, prefix: str = prefix) -> str | None:
                found = assets.get(asset_id)
                return f"{prefix}assets/{found.name}" if found else None

            children = [
                (c.node.title, prefix + files[c.node.id])
                for c in pages
                if c.node.parent_id == page.node.id
            ]
            meta = page.version.metadata_
            lead = (
                f'<p class="lead">{escape(str(meta["description"]))}</p>'
                if meta.get("description")
                else ""
            )
            back = (
                ""
                if single
                else f'<p class="back"><a href="{prefix}index.html">← {escape(space.name)}</a></p>'
            )
            body = f"{back}<h1>{escape(page.node.title)}</h1>{lead}" + render(
                page.version.content_json, Links(asset=asset, children=children)
            )
            zf.writestr(files[page.node.id], _doc(page.node.title, prefix, body))
        if not single:
            items = "".join(
                f'<li style="margin-left: {p.depth * 16}px"><a href="{escape(files[p.node.id])}">'
                f"{escape(p.node.title)}</a></li>"
                for p in pages
            )
            intro = f'<p class="lead">{escape(space.description)}</p>' if space.description else ""
            zf.writestr(
                "index.html",
                _doc(
                    space.name,
                    "",
                    f'<h1>{escape(space.name)}</h1>{intro}<ul class="tree">{items}</ul>',
                ),
            )
        for item in assets.values():
            zf.writestr(f"assets/{item.name}", item.data)
    return buffer.getvalue()
