"""What an export holds: the author's visible, published pages in tree order, with the
folder path each one sits in, and the files they use."""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioAsset, FolioNode, FolioSpace, FolioVersion, NodeKind
from radicle.folio.services import access
from radicle.platform.db.models import User
from radicle.platform.storage import get_storage

READABLE = (NodeKind.page, NodeKind.blog_post)


@dataclass(frozen=True)
class ExportPage:
    node: FolioNode
    version: FolioVersion
    path: tuple[str, ...]  # slugs of the folders and pages above it
    depth: int


@dataclass(frozen=True)
class ExportAsset:
    asset: FolioAsset
    data: bytes

    @property
    def name(self) -> str:
        """Its file name inside the export: unique, readable and safe."""
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", self.asset.filename).strip("-") or "file"
        return f"{str(self.asset.id)[:8]}-{safe}"


async def collect(
    db: AsyncSession, user: User, space: FolioSpace, node_id: uuid.UUID | None
) -> list[ExportPage]:
    rows = list(
        await db.scalars(
            select(FolioNode)
            .where(FolioNode.space_id == space.id, await access.node_filter(db, user))
            .where(FolioNode.archived_at.is_(None))
            .order_by(FolioNode.rank, FolioNode.id)
        )
    )
    by_parent: dict[uuid.UUID | None, list[FolioNode]] = {}
    for n in rows:
        by_parent.setdefault(n.parent_id, []).append(n)
    ordered: list[tuple[FolioNode, tuple[str, ...]]] = []

    def walk(parent: uuid.UUID | None, path: tuple[str, ...]) -> None:
        for n in by_parent.get(parent, []):
            ordered.append((n, path))
            walk(n.id, (*path, n.slug))

    walk(None, ())
    wanted = [
        (n, path)
        for n, path in ordered
        if n.kind in READABLE
        and n.published_version_id is not None
        and (node_id is None or n.id == node_id)
    ]
    out = []
    for n, path in wanted:
        version = await db.get_one(FolioVersion, n.published_version_id)
        # One page alone sits at the root of its export.
        kept = path if node_id is None else ()
        out.append(ExportPage(n, version, kept, len(kept)))
    return out


def asset_ids(doc: dict[str, Any]) -> list[str]:
    """Every asset a document points at, in order, once."""
    found: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        asset = (node.get("attrs") or {}).get("assetId")
        if asset and asset not in found:
            found.append(str(asset))
        for child in node.get("content") or []:
            walk(child)

    walk(doc)
    return found


async def owned_asset(db: AsyncSession, pages: list[ExportPage], raw: str) -> FolioAsset | None:
    """The asset if it is one of these pages' files or covers; never another page's file,
    even if a document names its id."""
    try:
        asset = await db.get(FolioAsset, uuid.UUID(raw))
    except ValueError:
        return None
    if asset is None:
        return None
    mine = asset.node_id in {p.node.id for p in pages}
    return asset if mine or asset.id in {p.node.cover_asset_id for p in pages} else None


async def load_assets(db: AsyncSession, pages: list[ExportPage]) -> dict[str, ExportAsset]:
    """The files of these pages (and their covers), by id."""
    ids: list[str] = []
    for p in pages:
        if p.node.cover_asset_id:
            ids.append(str(p.node.cover_asset_id))
        ids += asset_ids(p.version.content_json)
    out: dict[str, ExportAsset] = {}
    for raw in dict.fromkeys(ids):
        asset = await owned_asset(db, pages, raw)
        if asset is not None:
            out[raw] = ExportAsset(asset, await get_storage().get(asset.storage_key))
    return out
