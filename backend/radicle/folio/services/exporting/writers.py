"""Pick the writer for an export's format."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.exports import ExportFormat, FolioExport
from radicle.folio.db.models import FolioSpace
from radicle.folio.services.exporting import markdown
from radicle.folio.services.exporting.pages import ExportPage


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
    raise ValueError(f"{row.format.value} exports are not available yet")
