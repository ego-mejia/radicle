"""The public inbox form (/b/{slug}): settings, anti-spam, submission and tracking."""

import hashlib
import hmac
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core import crypto
from radicle.core.config import get_settings
from radicle.core.errors import Conflict, NotFound, ProblemError, ValidationFailed
from radicle.core.permissions import ProjectAccess
from radicle.db.models import (
    Captcha,
    Classification,
    InboxSettings,
    InboxSubmission,
    Origin,
    Project,
    ProjectRole,
    Status,
    StatusCategory,
    Ticket,
    TicketType,
    User,
    utcnow,
)
from radicle.services import altcha, attachments, images, tickets
from radicle.services import ticket_fields as fields

INBOX_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
PUBLIC_CLASSIFICATIONS = (Classification.complaint, Classification.suggestion, Classification.idea)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,38}[a-z0-9]$")
CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32: no I, L, O, U
CODE_LENGTH = 10  # 50 bits
PER_HOUR, PER_DAY = 5, 20
MIN_SECONDS = 3
MAX_LINKS = 5
MAX_FILE = 5 * 1024 * 1024
ATTACHMENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
CAPTCHA_VERIFY = {
    Captcha.turnstile: "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    Captcha.hcaptcha: "https://api.hcaptcha.com/siteverify",
}


class Rejected(ProblemError):
    """Spam and errors look the same to the sender: no hints."""

    status = 422
    code = "submission_rejected"

    def __init__(self, reason: str) -> None:
        super().__init__("We could not send it. Check the form and try again in a while.")
        self.reason = reason


# --- settings --------------------------------------------------------------------------------


def default_settings(project: Project) -> InboxSettings:
    return InboxSettings(
        project_id=project.id,
        enabled=False,
        public_slug=project.key.lower(),
        title=project.name,
        intro_md="",
        thank_you_md="",
        allowed_classifications=[c.value for c in PUBLIC_CLASSIFICATIONS],
        require_email=False,
        allow_attachments=True,
        max_attachments=3,
        captcha=Captcha.altcha,
        captcha_config={},
        auto_tags=[],
    )


async def get_settings_for(db: AsyncSession, project: Project) -> InboxSettings:
    found = await db.get(InboxSettings, project.id)
    return found or default_settings(project)


def _fail(name: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": name, "message": "invalid"}])


async def save_settings(
    db: AsyncSession, access: ProjectAccess, changes: dict[str, Any]
) -> tuple[InboxSettings, dict[str, Any], dict[str, Any]]:
    """Returns the settings and their (before, after) values without secrets."""
    project = access.project
    row = await db.get(InboxSettings, project.id)
    if row is None:
        row = default_settings(project)
        db.add(row)
    before = public_view(row)
    if "public_slug" in changes and changes["public_slug"] is not None:
        slug = str(changes["public_slug"]).strip().lower()
        if not SLUG_RE.match(slug):
            raise _fail("public_slug", "The slug is 2 to 40 lowercase letters, digits or dashes.")
        taken = await db.scalar(
            select(InboxSettings.project_id).where(
                InboxSettings.public_slug == slug, InboxSettings.project_id != project.id
            )
        )
        if taken:
            raise Conflict(f"/b/{slug} is taken by another project.", code="slug_taken")
        row.public_slug = slug
    for name in ("enabled", "require_email", "allow_attachments"):
        if changes.get(name) is not None:
            setattr(row, name, bool(changes[name]))
    for name, limit in (("title", 150), ("intro_md", 5000), ("thank_you_md", 5000)):
        if changes.get(name) is not None:
            text = str(changes[name])
            if len(text) > limit:
                raise _fail(name, f"{name} is up to {limit} characters.")
            setattr(row, name, text)
    if changes.get("allowed_classifications") is not None:
        chosen = [str(c) for c in changes["allowed_classifications"]]
        allowed = {c.value for c in PUBLIC_CLASSIFICATIONS}
        if not chosen or set(chosen) - allowed:
            raise _fail(
                "allowed_classifications",
                "Pick at least one of complaint, suggestion and idea (experiments are for the "
                "team).",
            )
        row.allowed_classifications = chosen
    if changes.get("max_attachments") is not None:
        n = int(changes["max_attachments"])
        if not 0 <= n <= 5:
            raise _fail("max_attachments", "Up to 5 files per submission.")
        row.max_attachments = n
    if changes.get("auto_tags") is not None:
        row.auto_tags = fields.normalize_tags(changes["auto_tags"])
    if changes.get("captcha") is not None:
        row.captcha = Captcha(changes["captcha"])
    if changes.get("captcha_site_key") is not None or changes.get("captcha_secret"):
        config = dict(row.captcha_config or {})
        if changes.get("captcha_site_key") is not None:
            config["site_key"] = str(changes["captcha_site_key"]).strip()
        if changes.get("captcha_secret"):
            config["secret"] = crypto.encrypt(str(changes["captcha_secret"]).strip())
        row.captcha_config = config
    if row.captcha in CAPTCHA_VERIFY and not (
        row.captcha_config.get("site_key") and row.captcha_config.get("secret")
    ):
        raise _fail("captcha", f"{row.captcha.value} needs its site key and secret.")
    row.updated_at = utcnow()
    await db.flush()
    return row, before, public_view(row)


def public_view(row: InboxSettings) -> dict[str, Any]:
    """Settings as shown to admins and the audit log: never the captcha secret."""
    return {
        "enabled": row.enabled,
        "public_slug": row.public_slug,
        "title": row.title,
        "intro_md": row.intro_md,
        "thank_you_md": row.thank_you_md,
        "allowed_classifications": list(row.allowed_classifications or []),
        "require_email": row.require_email,
        "allow_attachments": row.allow_attachments,
        "max_attachments": row.max_attachments,
        "captcha": row.captcha.value if row.captcha else "altcha",
        "captcha_site_key": (row.captcha_config or {}).get("site_key"),
        "captcha_has_secret": bool((row.captcha_config or {}).get("secret")),
        "auto_tags": list(row.auto_tags or []),
    }


# --- public side -----------------------------------------------------------------------------


async def load_form(db: AsyncSession, slug: str) -> tuple[Project, InboxSettings]:
    row = await db.scalar(select(InboxSettings).where(InboxSettings.public_slug == slug.lower()))
    project = await db.get(Project, row.project_id) if row else None
    if row is None or project is None or not row.enabled or project.archived_at is not None:
        raise NotFound("This page does not exist.", code="form_not_found")
    return project, row


def _key(purpose: bytes) -> bytes:
    return hashlib.sha256(purpose + get_settings().signing_key).digest()


def form_token(slug: str, now: float | None = None) -> str:
    """Signed load time, to reject forms sent faster than a person can."""
    ts = int(now if now is not None else time.time())
    sig = hmac.new(_key(b"form:"), f"{slug}|{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    return f"{ts}.{sig}"


def token_age(slug: str, token: str, now: float | None = None) -> float | None:
    try:
        ts_text, sig = token.split(".", 1)
        ts = int(ts_text)
    except ValueError:
        return None
    expected = hmac.new(_key(b"form:"), f"{slug}|{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(expected, sig):
        return None
    return (now if now is not None else time.time()) - ts


def ip_hash(ip: str, day: date | None = None) -> str:
    """The IP is never stored: a hash with a salt that changes every day."""
    salt = hmac.new(
        _key(b"ip-salt:"), (day or utcnow().date()).isoformat().encode(), hashlib.sha256
    ).digest()
    return hashlib.sha256(salt + ip.encode()).hexdigest()


async def _rate_ok(db: AsyncSession, hashed: str) -> bool:
    now = utcnow()
    hour = await db.scalar(
        select(func.count()).where(
            InboxSubmission.ip_hash == hashed, InboxSubmission.created_at > now - timedelta(hours=1)
        )
    )
    day = await db.scalar(
        select(func.count()).where(
            InboxSubmission.ip_hash == hashed, InboxSubmission.created_at > now - timedelta(days=1)
        )
    )
    return int(hour or 0) < PER_HOUR and int(day or 0) < PER_DAY


async def _captcha_ok(db: AsyncSession, row: InboxSettings, answer: str | None, ip: str) -> bool:
    if row.captcha is Captcha.none:
        return True
    if row.captcha is Captcha.altcha:
        return (await altcha.verify(db, answer)).ok
    if not answer:
        return False
    secret = crypto.decrypt(row.captcha_config["secret"])
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            CAPTCHA_VERIFY[row.captcha],
            data={"secret": secret, "response": answer, "remoteip": ip},
        )
    return bool(r.status_code == 200 and r.json().get("success"))


MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<])")


def escape_markdown(text: str) -> str:
    """Sent text is shown as typed: markdown and HTML are escaped, line breaks kept."""
    lines = [MD_SPECIAL.sub(r"\\\1", line) for line in text.replace("\r\n", "\n").split("\n")]
    return "  \n".join(lines)


@dataclass
class Submission:
    classification: str
    title: str
    description: str
    name: str | None = None
    email: str | None = None
    honeypot: str | None = None
    token: str = ""
    captcha: str | None = None
    files: list[tuple[str, bytes]] = field(default_factory=list)


@dataclass
class Invalid(Exception):
    """Field errors a person can fix (not spam)."""

    errors: dict[str, str]


def _validate(sub: Submission, row: InboxSettings) -> dict[str, str]:
    errors: dict[str, str] = {}
    if sub.classification not in (row.allowed_classifications or []):
        errors["classification"] = "choose"
    title = " ".join(sub.title.split())
    if not 5 <= len(title) <= 150:
        errors["title"] = "length"
    if len(sub.description) > 10_000:
        errors["description"] = "length"
    if sub.name and len(sub.name) > 120:
        errors["name"] = "length"
    email = (sub.email or "").strip()
    if row.require_email and not email:
        errors["email"] = "required"
    elif email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors["email"] = "invalid"
    if sub.files:
        if not row.allow_attachments or len(sub.files) > row.max_attachments:
            errors["files"] = "count"
        elif any(len(data) > MAX_FILE for _, data in sub.files):
            errors["files"] = "size"
        elif any(images.detect(data) not in ATTACHMENT_TYPES for _, data in sub.files):
            errors["files"] = "type"
    return errors


async def submit(
    db: AsyncSession, project: Project, row: InboxSettings, sub: Submission, ip: str
) -> Ticket:
    """Anti-spam first (all failures look alike), then field checks, then the Draft."""
    hashed = ip_hash(ip)
    if sub.honeypot:
        raise Rejected("honeypot")
    age = token_age(row.public_slug, sub.token)
    if age is None or age < MIN_SECONDS or age > 86_400:
        raise Rejected("too fast")
    if not await _rate_ok(db, hashed):
        raise Rejected("rate")
    if len(re.findall(r"https?://", sub.description, re.I)) > MAX_LINKS:
        raise Rejected("links")
    errors = _validate(sub, row)
    if errors:
        raise Invalid(errors)
    if not await _captcha_ok(db, row, sub.captcha, ip):
        raise Rejected("captcha")

    inbox_user = await db.get(User, INBOX_USER_ID)
    if inbox_user is None:  # pragma: no cover - created by the migration
        raise Rejected("no inbox user")
    access = ProjectAccess(
        project=project,
        role=ProjectRole.member,
        user=inbox_user,
        permissions=frozenset({"ticket.create", "attachment.upload"}),
    )
    ticket = await tickets.create_ticket(
        db,
        access,
        tickets.NewTicket(
            type=TicketType.draft,
            title=" ".join(sub.title.split()),
            description_md=escape_markdown(sub.description.strip()),
            classification=Classification(sub.classification),
            origin=Origin.user,
            tags=list(row.auto_tags or []),
            submitter_name=(sub.name or "").strip() or None,
            submitter_email=(sub.email or "").strip() or None,
        ),
    )
    ticket.tracking_code = await _new_code(db)
    for filename, data in sub.files:
        await attachments.upload(
            db, access, ticket, filename=filename[:200] or "file", data=data, resize="medium"
        )
    db.add(InboxSubmission(project_id=project.id, ip_hash=hashed))
    await db.flush()
    return ticket


async def _new_code(db: AsyncSession) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not await db.scalar(select(Ticket.id).where(Ticket.tracking_code == code)):
            return code


@dataclass(frozen=True)
class Tracking:
    title: str
    classification: str
    created_at: Any
    state: str  # received, in_review, accepted, closed
    public_comment: str | None


async def tracking(db: AsyncSession, row: InboxSettings, code: str) -> Tracking:
    """What the sender may know: never keys, people, comments or where it went."""
    found = await db.execute(
        select(Ticket, Status.category)
        .join(Status, Status.id == Ticket.status_id)
        .where(
            Ticket.tracking_code == code.strip().upper(),
            Ticket.project_id == row.project_id,
            Ticket.deleted_at.is_(None),
        )
    )
    hit = found.first()
    if hit is None:
        raise NotFound("We do not know that code.", code="tracking_not_found")
    ticket, category = hit
    if ticket.converted_at is not None:
        state = "accepted"
    elif category is StatusCategory.done:
        state = "closed"
    elif category is StatusCategory.in_progress:
        state = "in_review"
    else:
        state = "received"
    return Tracking(
        title=ticket.title,
        classification=ticket.classification.value if ticket.classification else "idea",
        created_at=ticket.created_at,
        state=state,
        public_comment=ticket.public_comment if state == "closed" else None,
    )
