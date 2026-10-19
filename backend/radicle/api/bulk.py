from typing import Any

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.api.jobs import JobOut, job_out
from radicle.api.schemas.common import Input, Output
from radicle.api.schemas.tickets import TicketOut
from radicle.api.ticket_views import ticket_out
from radicle.db.models import ProjectRole
from radicle.services import bulk, moving, tickets
from radicle.services.access import project_access

router = APIRouter(tags=["clone, move and bulk"])


class CloneIn(Input):
    target_project: str | None = Field(default=None, description="Default: same project")
    area_mapping: dict[str, str] = Field(
        default_factory=dict, description='{"Legal": "Compliance"} when areas differ'
    )
    include: list[str] = Field(
        default_factory=list,
        description="description, checklist_state, tags, custom_fields, collaborators, "
        "attachments, children",
    )


class MoveIn(Input):
    target_project: str
    area_mapping: dict[str, str] = Field(default_factory=dict)
    milestone: str | None = None
    status_mapping: dict[str, str] = Field(
        default_factory=dict, description='{"In Review": "QA"}; by name otherwise, else initial'
    )
    include_children: bool = True


class BulkIn(Input):
    keys: list[str] | None = None
    query: str | None = Field(default=None, description="RQL")
    operations: list[dict[str, Any]] = Field(
        description="set_field, clear_field, add_tag, remove_tag, transition, assign, "
        "add_collaborator"
    )
    dry_run: bool = False


class BulkTicketResult(Output):
    key: str
    ok: bool
    error: str | None


class BulkOut(Output):
    total: int
    dry_run: bool
    succeeded: int
    failed: int
    results: list[BulkTicketResult] = Field(description="Empty when it runs as a job")
    job: JobOut | None = Field(description="Set when more than 100 tickets run in the background")


@router.post("/tickets/{key}/clone", response_model=TicketOut, status_code=201)
async def clone_ticket(key: str, body: CloneIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Copy a ticket into its project or another one. The clone starts in the initial
    status, unassigned, with a `clones` link to the original."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, need=ProjectRole.member, write=True
    )
    target = access
    if body.target_project and body.target_project.upper() != access.project.key.upper():
        target = await project_access(
            db, principal.user, body.target_project, need=ProjectRole.member, write=True
        )
    clone = await moving.clone_ticket(
        db,
        access,
        ticket,
        target=target,
        area_mapping=body.area_mapping,
        include=body.include,
    )
    return await ticket_out(db, clone, viewer=principal.user)


@router.post("/tickets/{key}/move", response_model=TicketOut)
async def move_ticket(key: str, body: MoveIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Move to another project (admin here, member there). The ticket gets a new key;
    the old one keeps resolving to it."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, need=ProjectRole.admin, write=True
    )
    await moving.move_ticket(
        db,
        access,
        ticket,
        target_key=body.target_project,
        area_mapping=body.area_mapping,
        milestone=body.milestone,
        status_mapping=body.status_mapping,
        include_children=body.include_children,
    )
    out = await ticket_out(db, ticket, viewer=principal.user)
    out.moved_from = key.strip().upper()
    return out


@router.post("/tickets/bulk", response_model=BulkOut)
async def bulk_update(
    body: BulkIn, principal: CurrentPrincipal, db: Db, settings: AppSettings, response: Response
) -> BulkOut:
    """Same operations on up to 500 tickets (by keys or RQL). `dry_run` shows what would
    happen without changing anything. More than 100 tickets run as a job: 202 + job."""
    result = await bulk.bulk_update(
        db,
        principal.user,
        keys=body.keys,
        query=body.query,
        operations=body.operations,
        dry_run=body.dry_run,
        timezone=settings.timezone,
    )
    if result.job is not None:
        response.status_code = 202
    return BulkOut(
        total=result.total,
        dry_run=result.dry_run,
        succeeded=result.succeeded,
        failed=len(result.results) - result.succeeded,
        results=[BulkTicketResult(**r.json()) for r in result.results],
        job=job_out(result.job) if result.job else None,
    )
