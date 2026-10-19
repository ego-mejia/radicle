"""Attachments: upload, resize, variants, signed download URLs and deletion."""

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.config import get_settings
from radicle.core.errors import Conflict, Forbidden, NotFound, ProblemError, ValidationFailed
from radicle.db.models import (
    Attachment,
    Comment,
    EventType,
    Project,
    ProjectRole,
    Ticket,
    User,
    utcnow,
)
from radicle.services import history, images, queue
from radicle.services.access import ProjectAccess, check_access, role_in
from radicle.services.tickets import bump
from radicle.storage import get_storage

VARIANTS_JOB = "attachment_variants"
URL_SECONDS = 300
FILENAME_MAX = 200


class PayloadTooLarge(ProblemError):
    status = 413
    code = "payload_too_large"


@dataclass(frozen=True)
class AttachmentAccess:
    access: ProjectAccess
    ticket: Ticket
    attachment: Attachment


def max_bytes() -> int:
    return get_settings().max_upload_mb * 1024 * 1024


def check_size(size: int, limit: int | None = None) -> None:
    limit = limit or max_bytes()
    if size > limit:
        raise PayloadTooLarge(
            f"The file is {size / 1024 / 1024:.1f} MB; the limit is {limit // 1024 // 1024} MB."
        )


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


def storage_key(attachment: Attachment, ticket: Ticket, variant: str = "original") -> str:
    return f"{ticket.project_id}/{ticket.id}/{attachment.id}/{variant}"


async def upload(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    filename: str,
    data: bytes,
    comment_id: uuid.UUID | None = None,
    resize: str | None = None,
    limit: int | None = None,
) -> Attachment:
    check_size(len(data), limit)
    if not data:
        raise ValidationFailed("The file is empty.", errors=[{"field": "file", "message": "empty"}])
    if comment_id is not None:
        comment = await db.get(Comment, comment_id)
        if comment is None or comment.ticket_id != ticket.id:
            raise ValidationFailed(
                "comment_id is not a comment of this ticket.",
                errors=[{"field": "comment_id", "message": "unknown"}],
            )
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
    attachment = Attachment(
        id=uuid.uuid4(),
        ticket_id=ticket.id,
        comment_id=comment_id,
        uploader_id=access.user.id,
        filename=_filename(filename),
        mime_type=mime_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_key="",
        width=width,
        height=height,
        variants={},
    )
    attachment.storage_key = storage_key(attachment, ticket)
    await get_storage().put(attachment.storage_key, data, mime_type)
    db.add(attachment)
    history.record(
        db,
        ticket,
        access.user,
        EventType.attachment_added,
        field="attachments",
        new={"id": str(attachment.id), "filename": attachment.filename, "size": len(data)},
    )
    bump(ticket)
    await db.flush()
    if images.is_image(mime_type):
        await queue.enqueue(db, VARIANTS_JOB, attachment_id=str(attachment.id))
    return attachment


async def list_attachments(db: AsyncSession, ticket_ids: list[uuid.UUID]) -> list[Attachment]:
    if not ticket_ids:
        return []
    return list(
        await db.scalars(
            select(Attachment)
            .where(Attachment.ticket_id.in_(ticket_ids), Attachment.deleted_at.is_(None))
            .order_by(Attachment.created_at, Attachment.id)
        )
    )


async def load(
    db: AsyncSession,
    user: User,
    attachment_id: uuid.UUID,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
) -> AttachmentAccess:
    """The attachment if the user may see its ticket; 404 otherwise, like tickets."""
    attachment = await db.get(Attachment, attachment_id)
    not_found = NotFound(f"Attachment {attachment_id} not found.", code="attachment_not_found")
    if attachment is None or attachment.deleted_at is not None:
        raise not_found
    ticket = await db.get(Ticket, attachment.ticket_id)
    if ticket is None or ticket.deleted_at is not None:
        raise not_found
    project = await db.get(Project, ticket.project_id)
    if project is None:  # pragma: no cover - foreign key
        raise not_found
    role = await role_in(db, user, project)
    if role is None:
        raise not_found
    access = check_access(project, role, user, need=need, write=write)
    return AttachmentAccess(access, ticket, attachment)


async def resize(db: AsyncSession, aa: AttachmentAccess, preset: str) -> Attachment:
    """Shrink an uploaded image in place. Never enlarges."""
    attachment, ticket = aa.attachment, aa.ticket
    if not images.is_image(attachment.mime_type):
        raise ValidationFailed(
            "Only images can be resized.", errors=[{"field": "preset", "message": "not an image"}]
        )
    limit = images.PRESETS.get(preset)
    if preset not in images.PRESETS or limit is None:
        raise ValidationFailed(
            "Use preset large, medium or small.",
            errors=[{"field": "preset", "message": "invalid"}],
        )
    current = max(attachment.width or 0, attachment.height or 0)
    if current <= limit:
        raise Conflict(
            f"{attachment.filename} is already {attachment.width}x{attachment.height}; "
            f"{preset} ({limit} px) would not make it smaller. Images are never enlarged.",
            code="not_smaller",
        )
    data = await get_storage().get(attachment.storage_key)
    processed = images.process(data, attachment.mime_type, preset)
    old_size = attachment.size_bytes
    await get_storage().put(attachment.storage_key, processed.data, attachment.mime_type)
    attachment.size_bytes = len(processed.data)
    attachment.sha256 = hashlib.sha256(processed.data).hexdigest()
    attachment.width, attachment.height = processed.width, processed.height
    history.record(
        db,
        ticket,
        aa.access.user,
        EventType.attachment_resized,
        field="attachments",
        old={"id": str(attachment.id), "size": old_size},
        new={"id": str(attachment.id), "size": attachment.size_bytes, "preset": preset},
    )
    bump(ticket)
    await db.flush()
    await queue.enqueue(db, VARIANTS_JOB, attachment_id=str(attachment.id))
    return attachment


async def delete(db: AsyncSession, aa: AttachmentAccess) -> None:
    """Uploader or project admin. The record stays (history), the bytes go."""
    attachment = aa.attachment
    if attachment.uploader_id != aa.access.user.id and not aa.access.at_least(ProjectRole.admin):
        raise Forbidden(
            "Only whoever uploaded it or a project admin can delete this attachment.",
            code="not_uploader",
        )
    attachment.deleted_at = utcnow()
    history.record(
        db,
        aa.ticket,
        aa.access.user,
        EventType.attachment_removed,
        field="attachments",
        old={"id": str(attachment.id), "filename": attachment.filename},
    )
    bump(aa.ticket)
    await db.flush()
    storage = get_storage()
    for key in [attachment.storage_key, *(v["key"] for v in attachment.variants.values())]:
        await storage.delete(key)


@queue.handler(VARIANTS_JOB)
async def make_variants(db: AsyncSession, attachment_id: str) -> None:
    """thumb (320 px) and preview (1280 px) webp copies of an image."""
    attachment = await db.get(Attachment, uuid.UUID(attachment_id))
    if attachment is None or attachment.deleted_at is not None:
        return
    ticket = await db.get(Ticket, attachment.ticket_id)
    if ticket is None:  # pragma: no cover - foreign key
        return
    storage = get_storage()
    data = await storage.get(attachment.storage_key)
    variants = {}
    for name, side in images.VARIANTS.items():
        made = images.variant(data, side)
        key = storage_key(attachment, ticket, name)
        await storage.put(key, made.data, made.mime_type)
        variants[name] = {
            "key": key,
            "width": made.width,
            "height": made.height,
            "size_bytes": len(made.data),
        }
    attachment.variants = variants
    await db.flush()


# --- signed URLs ---------------------------------------------------------------------------


def _signature(attachment_id: uuid.UUID, variant: str, expires: int) -> str:
    message = f"{attachment_id}:{variant}:{expires}".encode()
    return hmac.new(get_settings().signing_key, message, hashlib.sha256).hexdigest()[:32]


def signed_query(attachment_id: uuid.UUID, variant: str, now: float | None = None) -> str:
    expires = int((now or time.time()) + URL_SECONDS)
    sig = _signature(attachment_id, variant, expires)
    return f"variant={variant}&expires={expires}&sig={sig}"


def check_signature(
    attachment_id: uuid.UUID, variant: str, expires: int, sig: str, now: float | None = None
) -> bool:
    if expires < (now or time.time()):
        return False
    return hmac.compare_digest(_signature(attachment_id, variant, expires), sig)


def variant_key(attachment: Attachment, variant: str) -> tuple[str, str]:
    """Storage key and MIME type of a variant; falls back to the original while the
    worker has not made it yet."""
    if variant != "original" and variant in attachment.variants:
        return attachment.variants[variant]["key"], "image/webp"
    return attachment.storage_key, attachment.mime_type
