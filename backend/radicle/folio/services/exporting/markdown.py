"""Markdown export: a zip with one .md per page in its folders, metadata as front matter,
and the files under assets/ with the links pointing at them."""

import io
import json
import re
import zipfile

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services.exporting.pages import ExportAsset, ExportPage, load_assets

_ASSET_LINK = re.compile(r"\(asset:([0-9a-f-]{36})")
_DIRECTIVE = re.compile(r"^::(file|video)(\{.*\})\s*$", re.M)
_ATTR = re.compile(r'(\w+)=(?:"((?:[^"\\]|\\.)*)"|(\S+?))(?=[\s}])')


def front_matter(page: ExportPage, cover: str | None) -> str:
    """YAML front matter; each value is JSON, which YAML reads as is."""
    fields: dict[str, object] = {
        "title": page.node.title,
        "version": page.version.number,
        "published_at": page.node.published_at.isoformat() if page.node.published_at else None,
    }
    if cover:
        fields["cover"] = cover
    fields.update(sorted(page.version.metadata_.items()))
    lines = [f"{k}: {json.dumps(v, ensure_ascii=False, default=str)}" for k, v in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def _relink(md: str, prefix: str, assets: dict[str, ExportAsset]) -> str:
    def link(match: re.Match[str]) -> str:
        found = assets.get(match.group(1))
        return f"({prefix}assets/{found.name}" if found else match.group(0)

    def directive(match: re.Match[str]) -> str:
        attrs = {m[0]: m[1] or m[2] for m in _ATTR.findall(match.group(2))}
        found = assets.get(attrs.get("asset", ""))
        if not found:
            return match.group(0)
        text = attrs.get("name") or attrs.get("caption") or found.asset.filename
        return f"[{text}]({prefix}assets/{found.name})"

    return _DIRECTIVE.sub(directive, _ASSET_LINK.sub(link, md))


def unique(stem: str, ext: str, used: set[str]) -> str:
    """`stem` + `ext`, or with -2, -3... when two pages share a slug in one folder."""
    name, n = f"{stem}{ext}", 1
    while name in used:
        n += 1
        name = f"{stem}-{n}{ext}"
    used.add(name)
    return name


async def write(db: AsyncSession, pages: list[ExportPage]) -> bytes:
    assets = await load_assets(db, pages)
    buffer = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for page in pages:
            prefix = "../" * page.depth
            cover = assets.get(str(page.node.cover_asset_id))
            head = front_matter(page, f"{prefix}assets/{cover.name}" if cover else None)
            body = _relink(page.version.content_md, prefix, assets)
            zf.writestr(unique("/".join((*page.path, page.node.slug)), ".md", used), head + body)
        for item in assets.values():
            zf.writestr(f"assets/{item.name}", item.data)
    return buffer.getvalue()
