"""Folio assets (Folio 1.2): images, files and video for pages, in the shared storage.
Images are cleaned and shrunk to the chosen size, like Docket's attachments."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioAsset, FolioNode
from radicle.folio.services import access, nodes
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ProblemError, ValidationFailed
from radicle.platform.services import images
from radicle.platform.storage import get_storage

FILENAME_MAX = 200
# Shown in the page; everything else downloads (SVG and HTML could run scripts).
INLINE_TYPES = frozenset(
    {*images.IMAGE_TYPES, "application/pdf", "video/mp4", "video/webm", "video/ogg"}
)


class PayloadTooLarge(ProblemError):
    status = 413
    code = "payload_too_large"


def max_bytes() -> int:
    return get_settings().max_upload_mb * 1024 * 1024


def _filename(name: str) -> str:
    clean = name.replace("\\", "/").rsplit("/", 1)[-1].strip() or "file"
    return "".join(ch for ch in clean if ch.isprintable())[:FILENAME_MAX]


def _preset(value: str | None) -> str:
    preset = value or get_settings().image_default_resize
    if preset not in images.PRESETS:
        raise ValidationFailed(
            f"Unknown size '{preset}'. Use: {', '.join(images.PRESETS)}.",
            errors=[{"field": "resize", "message": "invalid"}],
        )
    return preset


async def upload(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    filename: str,
    data: bytes,
    resize: str | None = None,
) -> FolioAsset:
    await access.require_edit(db, user, node)
    limit = max_bytes()
    if len(data) > limit:
        raise PayloadTooLarge(
            f"The file is {len(data) / 1024 / 1024:.1f} MB; "
            f"the limit is {limit // 1024 // 1024} MB."
        )
    if not data:
        raise ValidationFailed("The file is empty.", errors=[{"field": "file", "message": "empty"}])
    mime_type = images.detect(data)
    width = height = None
    if images.is_image(mime_type):
        try:
            processed = images.process(data, mime_type, _preset(resize))
        except (OSError, ValueError) as exc:
            raise ValidationFailed(
                f"The image could not be read: {exc}.",
                errors=[{"field": "file", "message": "invalid image"}],
            ) from None
        data, width, height = processed.data, processed.width, processed.height
    asset = FolioAsset(
        id=uuid.uuid4(),
        node_id=node.id,
        uploader_id=user.id,
        filename=_filename(filename),
        mime_type=mime_type,
        size_bytes=len(data),
        storage_key="",
        width=width,
        height=height,
        variants={},
    )
    asset.storage_key = f"folio/{node.space_id}/{node.id}/{asset.id}/original"
    await get_storage().put(asset.storage_key, data, mime_type)
    db.add(asset)
    nodes.record(db, node, user, "asset_added", asset=str(asset.id), filename=asset.filename)
    await db.flush()
    return asset


async def load(db: AsyncSession, user: User, asset_id: uuid.UUID) -> FolioAsset:
    """An asset of a page you can see; 404 otherwise, as for the page itself."""
    asset = await db.get(FolioAsset, asset_id)
    if asset is not None and asset.node_id is not None:
        try:
            await nodes.get_node(db, user, asset.node_id)
        except NotFound:
            asset = None
    if asset is None or asset.node_id is None:
        raise NotFound(f"Asset {asset_id} not found.", code="asset_not_found")
    return asset
