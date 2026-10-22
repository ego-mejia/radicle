"""Pick the writer for an export's format."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.exports import ExportFormat, FolioExport
from radicle.folio.db.models import FolioSpace
from radicle.folio.services.exporting import browser, html, markdown, print_link, word
from radicle.folio.services.exporting.pages import ExportPage
from radicle.platform.config import get_settings


@dataclass(frozen=True)
class Output:
    data: bytes
    filename: str
    mime_type: str


async def write(
    db: AsyncSession, row: FolioExport, space: FolioSpace, pages: list[ExportPage]
) -> Output:
    name = pages[0].node.slug if row.node_id else space.key
    if row.format == ExportFormat.markdown:
        data = await markdown.write(db, pages)
        return Output(data, f"{name}-markdown.zip", "application/zip")
    if row.format == ExportFormat.html:
        data = await html.write(db, space, pages, single=row.node_id is not None)
        return Output(data, f"{name}-html.zip", "application/zip")
    if row.format == ExportFormat.docx:
        found = await _visual_pictures(pages)
        data = await word.write(db, pages, lambda n: found.get(id(n)))
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return Output(data, f"{name}.docx", mime)
    if row.format == ExportFormat.pdf:
        settings = get_settings()
        base = (settings.internal_url or settings.base_url).rstrip("/")
        data = await browser.pdf(f"{base}/print/{print_link.token(row.id)}")
        return Output(data, f"{name}.pdf", "application/pdf")
    raise ValueError(f"{row.format.value} exports are not available yet")


async def _visual_pictures(pages: list[ExportPage]) -> dict[int, bytes]:
    """Pictures of the visuals in these pages, by the id() of their node, for Word. Without
    a browser Word keeps their description."""
    visuals: list[dict[str, Any]] = []

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") == "visual":
            visuals.append(node)
        for child in node.get("content") or []:
            walk(child)

    for page in pages:
        walk(page.version.content_json)
    if not visuals:
        return {}
    try:
        taken = await browser.shots([str((v.get("attrs") or {}).get("code", "")) for v in visuals])
    except Exception:  # no Chromium here: descriptions only
        return {}
    return {id(v): shot for v, shot in zip(visuals, taken, strict=True) if shot}
