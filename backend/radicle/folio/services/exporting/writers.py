"""Pick the writer for an export's format."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.exports import FolioExport
from radicle.folio.db.models import FolioSpace
from radicle.folio.services.exporting.pages import ExportPage


@dataclass(frozen=True)
class Output:
    data: bytes
    filename: str
    mime_type: str


async def write(
    db: AsyncSession, row: FolioExport, space: FolioSpace, pages: list[ExportPage]
) -> Output:
    raise ValueError(f"{row.format.value} exports are not available yet")
