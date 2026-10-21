"""Evaluate transition rules for one ticket and one actor.

Order (see the stage 2 spec): conditions decide whether a transition is offered,
validators check the ticket before it moves, post-functions run right after the move in
the same transaction, so a failing post-function undoes the whole transition.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    BlockedPolicy,
    Project,
    RuleKind,
    Status,
    StatusCategory,
    Ticket,
    TransitionRule,
    UserKind,
)
from radicle.docket.services.access import ProjectAccess
from radicle.docket.services.screens import ticket_has
from radicle.platform.services import markdown


@dataclass(frozen=True)
class RuleFailure:
    rule: str
    message: str

    def json(self) -> dict[str, str]:
        return {"rule": self.rule, "message": self.message}


@dataclass
class RuleContext:
    access: ProjectAccess
    ticket: Ticket
    blocked_by: list[str] = field(default_factory=list)
    comment: str | None = None

    @property
    def policy(self) -> BlockedPolicy:
        return self.access.project.blocked_policy


def conditions(rules: list[TransitionRule]) -> list[TransitionRule]:
    return [r for r in rules if r.kind is RuleKind.condition]


def failed_conditions(rules: list[TransitionRule], ctx: RuleContext) -> list[RuleFailure]:
    user = ctx.access.user
    ticket = ctx.ticket
    failures = []
    for rule in conditions(rules):
        kind = rule.rule_type
        if kind == "only_assignee" and ticket.assignee_id != user.id:
            failures.append(RuleFailure(kind, "Only the assignee can do this."))
        elif kind == "only_reporter" and ticket.reporter_id != user.id:
            failures.append(RuleFailure(kind, "Only the reporter can do this."))
        elif kind == "only_roles" and ctx.access.role.value not in rule.config["roles"]:
            roles = ", ".join(rule.config["roles"])
            failures.append(RuleFailure(kind, f"Only these roles can do this: {roles}."))
        elif kind == "only_user_kind" and user.kind.value != rule.config["kind"]:
            who = "people" if rule.config["kind"] == UserKind.human.value else "agents"
            failures.append(RuleFailure(kind, f"Only {who} can do this."))
        elif kind == "not_blocked" and ctx.blocked_by and ctx.policy is BlockedPolicy.enforce:
            failures.append(
                RuleFailure(kind, f"Blocked by {', '.join(ctx.blocked_by)}, which are not done.")
            )
    return failures


async def failed_validators(
    db: AsyncSession, rules: list[TransitionRule], ctx: RuleContext
) -> list[RuleFailure]:
    ticket = ctx.ticket
    failures = []
    for rule in rules:
        if rule.kind is not RuleKind.validator:
            continue
        kind = rule.rule_type
        if kind == "checklist_complete":
            pending = [
                i.text for i in markdown.parse_checklist(ticket.description_md) if not i.checked
            ]
            if pending:
                listed = "; ".join(f"'{text}'" for text in pending)
                failures.append(
                    RuleFailure(kind, f"{len(pending)} checklist items are still open: {listed}.")
                )
        elif kind == "field_required" and not await ticket_has(db, ticket, rule.config["field"]):
            failures.append(
                RuleFailure(kind, f"{rule.config['field']} must have a value before this move.")
            )
        elif kind == "has_estimate" and ticket.estimate_hours is None:
            failures.append(RuleFailure(kind, "The ticket needs an estimate (estimate_hours)."))
        elif kind == "children_done":
            open_children = await _open_children(db, ticket)
            if open_children:
                failures.append(
                    RuleFailure(
                        kind, f"These subtickets are not done yet: {', '.join(open_children)}."
                    )
                )
        elif kind == "has_worklog" and ticket.time_spent_minutes <= 0:
            failures.append(
                RuleFailure(kind, "Log time on the ticket first (at least one worklog).")
            )
        elif kind == "comment_required" and not (ctx.comment or "").strip():
            failures.append(RuleFailure(kind, "This move needs a comment saying why."))
    return failures


async def _open_children(db: AsyncSession, ticket: Ticket) -> list[str]:
    rows = await db.execute(
        select(Project.key, Ticket.number)
        .join(Status, Status.id == Ticket.status_id)
        .join(Project, Project.id == Ticket.project_id)
        .where(
            Ticket.parent_id == ticket.id,
            Ticket.deleted_at.is_(None),
            Status.category != StatusCategory.done,
        )
        .order_by(Ticket.number)
    )
    return [f"{key}-{number}" for key, number in rows.all()]


def post_functions(rules: list[TransitionRule]) -> list[TransitionRule]:
    return [r for r in rules if r.kind is RuleKind.post_function]
