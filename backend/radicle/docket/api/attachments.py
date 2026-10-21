import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import RedirectResponse

from radicle.docket.api.schemas.attachments import AttachmentOut, ResizeIn
from radicle.docket.api.ticket_views import attachment_out
from radicle.docket.db.models import Attachment, ProjectRole
from radicle.docket.services import attachments, tickets
from radicle.platform.api.deps import AppSettings, CurrentPrincipal, Db, get_principal
from radicle.platform.api.schemas import Page
from radicle.platform.errors import NotFound, Unauthorized
from radicle.platform.services import images
from radicle.platform.storage import get_storage

router = APIRouter(tags=["attachments"])
MEMBER = ProjectRole.member
CHUNK = 1024 * 1024


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """Read at most limit + 1 bytes so a huge upload is refused without loading it all."""
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(CHUNK):
        size += len(chunk)
        chunks.append(chunk)
        if size > limit:
            break
    return b"".join(chunks)


@router.get("/tickets/{key}/attachments", response_model=Page[AttachmentOut])
async def list_attachments(key: str, principal: CurrentPrincipal, db: Db) -> Page[AttachmentOut]:
    access, ticket = await tickets.load_ticket(db, principal.user, key)
    ticket_key = f"{access.project.key}-{ticket.number}"
    rows = await attachments.list_attachments(db, [ticket.id])
    return Page(items=[attachment_out(a, ticket_key) for a in rows])


@router.post("/tickets/{key}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    file: Annotated[UploadFile, File(description="The file")],
    comment_id: Annotated[uuid.UUID | None, Form()] = None,
    resize: Annotated[
        str | None, Form(description="Images: original, large, medium or small")
    ] = None,
) -> AttachmentOut:
    """Upload a file (multipart). Images lose their EXIF and are shrunk to `resize`."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, write=True, permission="attachment.upload"
    )
    data = await _read_limited(file, attachments.max_bytes())
    attachment = await attachments.upload(
        db,
        access,
        ticket,
        filename=file.filename or "file",
        data=data,
        comment_id=comment_id,
        resize=resize,
    )
    await db.refresh(attachment, ["uploader"])
    return attachment_out(attachment, f"{access.project.key}-{ticket.number}")


@router.get("/attachments/{attachment_id}/content", response_model=None)
async def download_attachment(
    attachment_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Db,
    settings: AppSettings,
    variant: Annotated[str, Query(pattern="^(original|thumb|preview)$")] = "original",
    expires: int | None = None,
    sig: str | None = None,
) -> Response:
    """The bytes, with auth or with a valid signature from an attachment's `url`.
    Images are shown inline; everything else downloads."""
    signed = (
        expires is not None
        and sig is not None
        and attachments.check_signature(attachment_id, variant, expires, sig)
    )
    if signed:
        attachment = await db.get(Attachment, attachment_id)
        if attachment is None or attachment.deleted_at is not None:
            raise NotFound(f"Attachment {attachment_id} not found.", code="attachment_not_found")
    else:
        if (
            sig is not None
            and request.headers.get("authorization") is None
            and ("radicle_session" not in request.cookies)
        ):
            raise Unauthorized("This link expired. Open the ticket again to get a new one.")
        principal = await get_principal(request, response, db, settings)
        attachment = (await attachments.load(db, principal.user, attachment_id)).attachment
    key, mime_type = attachments.variant_key(attachment, variant)
    inline = images.is_image(mime_type)
    url = await get_storage().download_url(key, attachment.filename, inline=inline)
    if url is not None:
        return RedirectResponse(url, status_code=302)
    data = await get_storage().get(key)
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(attachment.filename)}",
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/attachments/{attachment_id}/resize", response_model=AttachmentOut)
async def resize_attachment(
    attachment_id: uuid.UUID, body: ResizeIn, principal: CurrentPrincipal, db: Db
) -> AttachmentOut:
    """Shrink an image already uploaded. It never gets bigger."""
    aa = await attachments.load(
        db, principal.user, attachment_id, write=True, permission="attachment.upload"
    )
    attachment = await attachments.resize(db, aa, body.preset)
    return attachment_out(attachment, f"{aa.access.project.key}-{aa.ticket.number}")


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    """The uploader or a project admin."""
    aa = await attachments.load(db, principal.user, attachment_id, write=True)
    await attachments.delete(db, aa)
    return Response(status_code=204)
