"""Docket's answer to platform's `authorize` and `visible` (ADR 0035): the same project
permission matrix and ticket visibility rule its own routes use, unchanged."""

from typing import Any

from sqlalchemy import ColumnElement, false
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.core import permissions
from radicle.docket.db.models import Project, Ticket
from radicle.platform.authz import Decision
from radicle.platform.db.models import User
from radicle.platform.errors import ProblemError


class DocketAuthz:
    """`resource` is a Project or a Ticket; a ticket is checked against its project and
    its security level, so a restricted ticket answers 404 like the API does."""

    app = "docket"

    async def check(
        self, db: AsyncSession, user: User, permission: str | None, resource: Any
    ) -> Decision:
        ticket = resource if isinstance(resource, Ticket) else None
        project = await db.get(Project, ticket.project_id) if ticket else resource
        if not isinstance(project, Project):
            return Decision(
                allowed=False,
                reason="Docket checks permissions on a project or a ticket.",
                status=404,
                code="unknown_resource",
            )
        try:
            await permissions.authorize(db, user, permission, project)
        except ProblemError as exc:
            return Decision.deny(exc)
        if ticket and not await permissions.can_see(db, user, ticket):
            return Decision(
                allowed=False,
                reason=f"Ticket {project.key}-{ticket.number} not found.",
                status=404,
                code="ticket_not_found",
            )
        return Decision.allow()

    def visible_clause(self, user: User, model: Any) -> ColumnElement[bool]:
        if model is Ticket:
            return permissions.visible_tickets_clause(user)
        if model is Project:
            return Project.id.in_(permissions.visible_project_ids(user))
        return false()
