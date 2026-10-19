"""Moving tickets through their workflow and changing their type."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, ValidationFailed
from radicle.db.models import (
    Area,
    BlockedPolicy,
    EventType,
    ProjectRole,
    Resolution,
    ScreenOperation,
    StatusCategory,
    Ticket,
    TicketType,
    TransitionRule,
    utcnow,
)
from radicle.services import (
    comments,
    history,
    relations,
    screens,
    tickets,
    timetracking,
    workflow_engine,
)
from radicle.services import ticket_fields as fields
from radicle.services.access import ProjectAccess
from radicle.services.rules import (
    RuleContext,
    RuleFailure,
    failed_conditions,
    failed_validators,
    post_functions,
)
from radicle.services.tickets import bump
from radicle.services.workflows import load_workflows


@dataclass(frozen=True)
class TicketWarning:
    code: str
    message: str
    by: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OptionView:
    """A transition from the current status, and why the caller may not run it."""

    option: workflow_engine.Option
    failures: list[RuleFailure]
    requires_comment: bool
    has_screen: bool = False

    @property
    def available(self) -> bool:
        return not self.failures


def _key(access: ProjectAccess, ticket: Ticket) -> str:
    return f"{access.project.key}-{ticket.number}"


async def _context(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, comment: str | None = None
) -> RuleContext:
    blockers = (await relations.blocked_by(db, [ticket.id])).get(ticket.id, [])
    return RuleContext(access=access, ticket=ticket, blocked_by=blockers, comment=comment)


async def transition_options(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket
) -> list[OptionView]:
    workflow = (await load_workflows(db, ticket.project_id))[ticket.type]
    ctx = await _context(db, access, ticket)
    views = []
    for option in workflow_engine.available(workflow, workflow.status_by_id(ticket.status_id)):
        rules = workflow.rules_for(option.transition)
        screen = await screens.find_screen(
            db, ticket.project_id, ticket.type, ScreenOperation.transition, option.transition.id
        )
        views.append(
            OptionView(
                option=option,
                failures=failed_conditions(rules, ctx),
                requires_comment=any(r.rule_type == "comment_required" for r in rules),
                has_screen=screen is not None and bool(screen.fields),
            )
        )
    return views


async def transition_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    to_status: str,
    resolution: Resolution | None = None,
    transition: str | None = None,
    comment: str | None = None,
    force: bool = False,
    fields: dict[str, Any] | None = None,
    log_minutes: int | None = None,
) -> list[TicketWarning]:
    """Conditions, blocked policy, validators, the move itself and post-functions,
    in that order. Anything that fails raises and nothing is saved."""
    workflow = (await load_workflows(db, ticket.project_id))[ticket.type]
    current = workflow.status_by_id(ticket.status_id)
    ctx = await _context(db, access, ticket, comment)
    can_force = force and access.at_least(ProjectRole.admin)
    allowed: list[workflow_engine.Option] = []
    refused: list[tuple[workflow_engine.Option, list[RuleFailure]]] = []
    for option in workflow_engine.available(workflow, current):
        failures = failed_conditions(workflow.rules_for(option.transition), ctx)
        if can_force:
            failures = [f for f in failures if f.rule != "not_blocked"]
        if failures:
            refused.append((option, failures))
        else:
            allowed.append(option)
    try:
        decision = workflow_engine.decide(
            workflow, current, to_status, resolution, transition, options=allowed
        )
    except Conflict as exc:
        target = workflow.status_named(to_status)
        blocked = [f for o, f in refused if target is not None and o.to_status.id == target.id]
        if exc.code != "invalid_transition" or not blocked or target is None:
            raise
        reasons = " ".join(f.message for f in blocked[0])
        raise Conflict(
            f"You cannot move {_key(access, ticket)} to '{target.name}': {reasons}",
            code="transition_unavailable",
            extra={"failed_rules": [f.json() for f in blocked[0]]},
        ) from None
    target = decision.option.to_status
    rules = workflow.rules_for(decision.option.transition)

    warnings: list[TicketWarning] = []
    forced = False
    if target.category in (StatusCategory.in_progress, StatusCategory.done) and ctx.blocked_by:
        blockers = ", ".join(ctx.blocked_by)
        if access.project.blocked_policy is BlockedPolicy.enforce:
            if not can_force:
                raise Conflict(
                    f"{_key(access, ticket)} is blocked by {blockers}, which are not done, and "
                    f"{access.project.key} does not let blocked tickets move to "
                    f"'{target.name}'. Finish the blockers first"
                    + (
                        ", or force it as admin with force=true."
                        if access.at_least(ProjectRole.admin)
                        else "."
                    ),
                    code="ticket_blocked",
                    extra={
                        "blocked_by": ctx.blocked_by,
                        "can_force": access.at_least(ProjectRole.admin),
                    },
                )
            forced = True
            warnings.append(
                TicketWarning(
                    code="forced",
                    message=f"Forced while blocked by {blockers}.",
                    by=ctx.blocked_by,
                )
            )
        else:
            warnings.append(
                TicketWarning(
                    code="blocked",
                    message=f"Moved while blocked by {blockers}, which are not done.",
                    by=ctx.blocked_by,
                )
            )

    await apply_screen(db, access, ticket, decision.option, fields or {})
    if log_minutes:
        await timetracking.add_worklog(
            db, access, ticket, minutes=log_minutes, description=f"Moving to {target.name}"
        )
    failures = await failed_validators(db, rules, ctx)
    if failures:
        raise Conflict(
            f"Cannot move {_key(access, ticket)} to '{target.name}': "
            + " ".join(f.message for f in failures),
            code="transition_rules_failed",
            extra={"failed_rules": [f.json() for f in failures]},
        )

    old = {"status": current.name, "resolution": _value(ticket.resolution)}
    ticket.status_id = target.id
    ticket.status = target
    if target.category is StatusCategory.done:
        ticket.resolution = decision.resolution
        if current.category is not StatusCategory.done or ticket.resolved_at is None:
            ticket.resolved_at = utcnow()
    else:
        ticket.resolution = None
        ticket.resolved_at = None
    new: dict[str, Any] = {
        "status": target.name,
        "resolution": _value(ticket.resolution),
        "transition": decision.option.transition.name,
    }
    if forced:
        new["forced"] = True
    history.record(
        db, ticket, access.user, EventType.status_changed, field="status", old=old, new=new
    )
    bump(ticket)
    await db.flush()

    if comment and comment.strip():
        await comments.add_comment(db, access, ticket, comment)
    await run_post_functions(
        db, access, ticket, post_functions(rules), from_name=current.name, to_name=target.name
    )
    return warnings


async def apply_screen(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    option: workflow_engine.Option,
    values: dict[str, Any],
) -> None:
    """Fields sent with the move are saved first (only those on the transition's screen),
    then every required field of that screen must have a value."""
    schema = await screens.form_schema(
        db, access.project, ticket.type, ScreenOperation.transition, option.transition
    )
    extra = [name for name in values if name not in schema.names()]
    if extra:
        raise ValidationFailed(
            f"'{option.transition.name}' does not take these fields: {', '.join(extra)}. "
            f"It takes: {', '.join(sorted(schema.names())) or 'none'}.",
            errors=[{"field": name, "message": "not on this screen"} for name in extra],
        )
    if values:
        changes: dict[str, Any] = {k: v for k, v in values.items() if not k.startswith("cf.")}
        custom = {k[3:]: v for k, v in values.items() if k.startswith("cf.")}
        if custom:
            changes["custom_fields"] = custom
        if isinstance(changes.get("due_date"), str):
            changes["due_date"] = date.fromisoformat(changes["due_date"])
        await tickets.update_ticket(
            db, access, ticket, changes, expected_version=None, enforce_screen=False
        )
    await screens.check_ticket(db, access.project, ticket, schema)


class _Blank(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


async def run_post_functions(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    rules: list[TransitionRule],
    *,
    from_name: str,
    to_name: str,
) -> None:
    for rule in rules:
        kind, config = rule.rule_type, rule.config
        changes: dict[str, Any] | None = None
        if kind == "assign_to_actor":
            changes = {"assignee": access.user.handle}
        elif kind == "unassign":
            changes = {"assignee": None}
        elif kind in ("set_field", "clear_field"):
            value = config.get("value") if kind == "set_field" else None
            name = config["field"]
            if name.startswith("cf."):
                changes = {"custom_fields": {name[3:]: value}}
            else:
                if name == "due_date" and isinstance(value, str):
                    value = date.fromisoformat(value)
                changes = {name: value}
        elif kind == "add_tag" and config["tag"] not in ticket.tags:
            changes = {"tags": [*ticket.tags, config["tag"]]}
        elif kind == "remove_tag" and config["tag"] in ticket.tags:
            changes = {"tags": [t for t in ticket.tags if t != config["tag"]]}
        elif kind == "add_comment":
            values = _Blank(actor=f"@{access.user.handle}", to=to_name)
            values["from"] = from_name
            body = config["template"].format_map(values)
            await comments.add_comment(db, access, ticket, body)
        if changes is not None:
            await tickets.update_ticket(
                db, access, ticket, changes, expected_version=None, enforce_screen=False
            )


async def change_type(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    new_type: TicketType,
    area: str | None = None,
) -> None:
    """Switch type: the ticket restarts at the new workflow's initial status."""
    if new_type is ticket.type:
        raise ValidationFailed(
            f"The ticket is already a {new_type.value}.",
            errors=[{"field": "type", "message": "unchanged"}],
        )
    project = access.project
    new_area = await fields.resolve_area(db, project, area) if area is not None else None
    if new_area is None and ticket.area_id is None:
        fields.require_area(new_type, None)

    workflows = await load_workflows(db, project.id)
    old_status = workflows[ticket.type].status_by_id(ticket.status_id)
    new_status = workflows[new_type].initial
    history.record(
        db,
        ticket,
        access.user,
        EventType.type_changed,
        field="type",
        old=ticket.type.value,
        new=new_type.value,
    )
    history.record(
        db,
        ticket,
        access.user,
        EventType.status_changed,
        field="status",
        old={"status": old_status.name, "resolution": _value(ticket.resolution)},
        new={"status": new_status.name, "resolution": None},
    )
    if new_area is not None and new_area.id != ticket.area_id:
        old_area = await db.get(Area, ticket.area_id) if ticket.area_id else None
        history.record(
            db,
            ticket,
            access.user,
            EventType.field_changed,
            field="area",
            old=old_area.name if old_area else None,
            new=new_area.name,
        )
        ticket.area_id = new_area.id
    ticket.type = new_type
    ticket.status_id = new_status.id
    ticket.status = new_status
    ticket.resolution = None
    ticket.resolved_at = None
    bump(ticket)
    await db.flush()


def _value(resolution: Resolution | None) -> str | None:
    return resolution.value if resolution is not None else None
