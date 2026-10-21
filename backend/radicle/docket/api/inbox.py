from fastapi import APIRouter, Query
from pydantic import Field

from radicle.docket.api.schemas.tickets import TicketOut, TicketSummary
from radicle.docket.api.ticket_views import summaries_out, ticket_out
from radicle.docket.db.models import Classification, Origin, Priority, ProjectRole, TicketType
from radicle.docket.services import inbox, public_form, tickets
from radicle.docket.services.access import project_access
from radicle.platform.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output
from radicle.platform.services import audit

router = APIRouter(tags=["inbox"])


class InboxOut(Output):
    tab: inbox.Tab
    counts: dict[str, int] = Field(description="Items per tab: new, in_review, approved, discarded")
    items: list[TicketSummary]


class ApproveIn(Input):
    type: TicketType = Field(description="task or bug")
    area: str
    milestone: str | None = None
    priority: Priority | None = None
    assignee: str | None = None


class DiscardIn(Input):
    public_comment: str | None = Field(
        default=None, description="Shown to the submitter on the tracking page"
    )


class DuplicateIn(Input):
    original: str = Field(description="Key of the ticket it duplicates")


@router.get("/projects/{key}/inbox", response_model=InboxOut)
async def get_inbox(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    tab: inbox.Tab = "new",
    classification: Classification | None = None,
    origin: Origin | None = None,
    sort: inbox.Sort = Query(default="votes", description="votes, age or score (impact*2-effort)"),
) -> InboxOut:
    """The project's drafts: new, in review, approved (converted) or discarded."""
    access = await project_access(db, principal.user, key)
    view = await inbox.inbox(
        db,
        principal.user,
        access.project,
        tab=tab,
        classification=classification,
        origin=origin,
        sort=sort,
    )
    return InboxOut(tab=tab, counts=view.counts, items=await summaries_out(db, view.tickets))


@router.post("/tickets/{key}/inbox/approve", response_model=TicketOut)
async def approve(key: str, body: ApproveIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Approve and convert in one step: the draft becomes a task or bug in the same ticket,
    keeping origin, classification, votes, comments and history."""
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.approve(
        db,
        access,
        ticket,
        key,
        to_type=body.type,
        area=body.area,
        milestone=body.milestone,
        priority=body.priority,
        assignee=body.assignee,
    )
    return await ticket_out(db, ticket, viewer=principal.user)


@router.post("/tickets/{key}/inbox/discard", response_model=TicketOut)
async def discard(key: str, body: DiscardIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.discard(db, access, ticket, key, public_comment=body.public_comment)
    return await ticket_out(db, ticket, viewer=principal.user)


@router.post("/tickets/{key}/inbox/duplicate", response_model=TicketOut)
async def duplicate(key: str, body: DuplicateIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Link as duplicate of `original`, close it and pass its voters to the original."""
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.mark_duplicate(db, access, ticket, key, body.original)
    return await ticket_out(db, ticket, viewer=principal.user)


class InboxSettingsOut(Output):
    enabled: bool
    public_slug: str
    public_url: str
    title: str
    intro_md: str
    thank_you_md: str
    allowed_classifications: list[str]
    require_email: bool
    allow_attachments: bool
    max_attachments: int
    captcha: str
    captcha_site_key: str | None
    captcha_has_secret: bool = Field(description="The secret is stored encrypted, never shown")
    auto_tags: list[str]


class InboxSettingsIn(Input):
    enabled: bool | None = None
    public_slug: str | None = None
    title: str | None = None
    intro_md: str | None = None
    thank_you_md: str | None = None
    allowed_classifications: list[str] | None = None
    require_email: bool | None = None
    allow_attachments: bool | None = None
    max_attachments: int | None = None
    captcha: str | None = Field(default=None, description="altcha, turnstile, hcaptcha or none")
    captcha_site_key: str | None = None
    captcha_secret: str | None = Field(default=None, description="Write only")
    auto_tags: list[str] | None = None


def _settings_out(view: dict[str, object], base_url: str) -> InboxSettingsOut:
    return InboxSettingsOut(
        **view,
        public_url=f"{base_url.rstrip('/')}/b/{view['public_slug']}",
    )


@router.get("/projects/{key}/inbox-settings", response_model=InboxSettingsOut)
async def get_inbox_settings(
    key: str, principal: CurrentPrincipal, db: Db, settings: AppSettings
) -> InboxSettingsOut:
    access = await project_access(db, principal.user, key, need=ProjectRole.admin)
    row = await public_form.get_settings_for(db, access.project)
    return _settings_out(public_form.public_view(row), settings.base_url)


@router.put("/projects/{key}/inbox-settings", response_model=InboxSettingsOut)
async def put_inbox_settings(
    key: str, body: InboxSettingsIn, principal: CurrentPrincipal, db: Db, settings: AppSettings
) -> InboxSettingsOut:
    """The public form at /b/{slug}: turn it on, texts, kinds, email, files, captcha."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    _, before, after = await public_form.save_settings(
        db, access, body.model_dump(exclude_unset=True)
    )
    audit.record(
        db,
        principal.user,
        "inbox.settings_change",
        target_type="inbox_settings",
        target_id=access.project.key,
        project_id=access.project.id,
        before=before,
        after=after,
    )
    return _settings_out(after, settings.base_url)
