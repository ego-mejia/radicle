"""Bulk edit: the same operations on many tickets, each in its own savepoint.

Up to 100 tickets run in the request; more run as a job with progress. Every ticket
goes through the normal edit rules (screens, transition rules), so the result reports
success or the exact error per ticket. `dry_run` does all of it and rolls back.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import Job, Project, Resolution, Ticket, User
from radicle.platform.errors import ProblemError, ValidationFailed
from radicle.platform.services import jobs, queue
from radicle.services import search, tickets, transitions
from radicle.services.access import ProjectAccess

MAX_TICKETS = 500
INLINE_MAX = 100
JOB = "bulk_update"
OPERATIONS = (
    "set_field",
    "clear_field",
    "add_tag",
    "remove_tag",
    "transition",
    "assign",
    "add_collaborator",
)


class _DryRun(Exception):
    """Raised inside the savepoint of a dry run so nothing is kept."""


@dataclass
class TicketResult:
    key: str
    ok: bool
    error: str | None = None

    def json(self) -> dict[str, Any]:
        return {"key": self.key, "ok": self.ok, "error": self.error}


@dataclass
class BulkResult:
    total: int
    dry_run: bool
    results: list[TicketResult] = field(default_factory=list)
    job: Job | None = None

    @property
    def succeeded(self) -> int:
        return sum(r.ok for r in self.results)


def check_operations(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not operations:
        raise ValidationFailed(
            "Send at least one operation.", errors=[{"field": "operations", "message": "empty"}]
        )
    for i, op in enumerate(operations):
        name = op.get("op")
        path = f"operations.{i}"
        if name not in OPERATIONS:
            raise ValidationFailed(
                f"Unknown operation '{name}'. Use {', '.join(OPERATIONS)}.",
                errors=[{"field": path, "message": "unknown"}],
            )
        needs = {
            "set_field": ("field",),
            "clear_field": ("field",),
            "add_tag": ("tag",),
            "remove_tag": ("tag",),
            "transition": ("to_status",),
            "assign": ("handle",),
            "add_collaborator": ("handle",),
        }[str(name)]
        missing = [k for k in needs if not op.get(k) and not (k == "handle" and name == "assign")]
        if missing:
            raise ValidationFailed(
                f"Operation {name} needs: {', '.join(missing)}.",
                errors=[{"field": path, "message": "incomplete"}],
            )
    return operations


async def resolve_keys(
    db: AsyncSession, user: User, keys: list[str] | None, query: str | None, timezone: str
) -> list[str]:
    if bool(keys) == bool(query):
        raise ValidationFailed(
            "Send either `keys` or `query` (RQL).",
            errors=[{"field": "keys", "message": "keys or query"}],
        )
    if keys:
        unique = list(dict.fromkeys(k.strip().upper() for k in keys))
    else:
        result = await search.search(
            db, user, query or "", limit=search.MAX_LIMIT, timezone=timezone
        )
        found = list(result.tickets)
        offset_cursor = result.next_cursor
        while offset_cursor and len(found) <= MAX_TICKETS:
            page = await search.search(
                db,
                user,
                query or "",
                limit=search.MAX_LIMIT,
                cursor=offset_cursor,
                timezone=timezone,
            )
            found += page.tickets
            offset_cursor = page.next_cursor
        rows = await db.execute(
            select(Project.id, Project.key).where(Project.id.in_({t.project_id for t in found}))
        )
        project_keys = dict(rows.all())
        unique = [f"{project_keys[t.project_id]}-{t.number}" for t in found]
    if len(unique) > MAX_TICKETS:
        raise ValidationFailed(
            f"Bulk edit takes at most {MAX_TICKETS} tickets; this selects {len(unique)}. "
            "Narrow the query.",
            code="too_many_tickets",
            errors=[{"field": "query", "message": "too many"}],
        )
    return unique


async def apply(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, op: dict[str, Any]
) -> None:
    name = op["op"]
    if name in ("set_field", "clear_field"):
        target = str(op["field"])
        value = op.get("value") if name == "set_field" else None
        changes: dict[str, Any] = (
            {"custom_fields": {target[3:]: value}} if target.startswith("cf.") else {target: value}
        )
        await tickets.update_ticket(db, access, ticket, changes, expected_version=None)
    elif name == "add_tag" and op["tag"] not in ticket.tags:
        await tickets.update_ticket(
            db, access, ticket, {"tags": [*ticket.tags, op["tag"]]}, expected_version=None
        )
    elif name == "remove_tag":
        tag = str(op["tag"]).lstrip("#").lower()
        if tag in ticket.tags:
            await tickets.update_ticket(
                db,
                access,
                ticket,
                {"tags": [t for t in ticket.tags if t != tag]},
                expected_version=None,
            )
    elif name == "transition":
        await transitions.transition_ticket(
            db,
            access,
            ticket,
            to_status=str(op["to_status"]),
            resolution=Resolution(op["resolution"]) if op.get("resolution") else None,
            comment=op.get("comment"),
        )
    elif name == "assign":
        await tickets.update_ticket(
            db, access, ticket, {"assignee": op.get("handle") or None}, expected_version=None
        )
    elif name == "add_collaborator":
        await tickets.add_collaborator(db, access, ticket, str(op["handle"]))


async def run_one(
    db: AsyncSession, user: User, key: str, operations: list[dict[str, Any]], dry_run: bool
) -> TicketResult:
    try:
        async with db.begin_nested():
            access, ticket = await tickets.load_ticket(
                db, user, key, write=True, permission="ticket.bulk_edit"
            )
            for op in operations:
                await apply(db, access, ticket, op)
            if dry_run:
                raise _DryRun
    except _DryRun:
        return TicketResult(key, True)
    except ProblemError as exc:
        return TicketResult(key, False, exc.detail)
    return TicketResult(key, True)


async def bulk_update(
    db: AsyncSession,
    user: User,
    *,
    keys: list[str] | None,
    query: str | None,
    operations: list[dict[str, Any]],
    dry_run: bool,
    timezone: str = "UTC",
) -> BulkResult:
    operations = check_operations(operations)
    selected = await resolve_keys(db, user, keys, query, timezone)
    result = BulkResult(total=len(selected), dry_run=dry_run)
    if dry_run or len(selected) <= INLINE_MAX:
        for key in selected:
            result.results.append(await run_one(db, user, key, operations, dry_run))
        return result
    job = await jobs.create_job(
        db, user, JOB, total=len(selected), params={"keys": selected, "operations": operations}
    )
    await queue.enqueue(db, JOB, job_id=str(job.id))
    result.job = job
    return result


@queue.handler(JOB)
async def run_bulk_job(db: AsyncSession, job_id: str) -> None:
    job = await db.get(Job, uuid.UUID(job_id))
    if job is None or job.finished_at is not None:
        return
    user = await db.get(User, job.created_by)
    if user is None:  # pragma: no cover - users are never deleted
        return
    jobs.start(job)
    await db.commit()
    results = []
    for i, key in enumerate(job.params["keys"]):
        outcome = await run_one(db, user, key, job.params["operations"], dry_run=False)
        results.append(outcome.json())
        job.progress = i + 1
        if (i + 1) % 10 == 0:
            await db.commit()
    jobs.finish(job, {"results": results, "succeeded": sum(r["ok"] for r in results)})
    await db.commit()
