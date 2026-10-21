"""Folio's answer to platform's `authorize` (ADR 0035): the global role decides, until
spaces and pages bring their own permissions in phase 1."""

from typing import Any

from sqlalchemy import ColumnElement, false
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import ROLE_RANK, FolioRole
from radicle.folio.services import roles
from radicle.platform.authz import Decision
from radicle.platform.db.models import User

# Permission -> lowest global role that has it.
NEEDS: dict[str, FolioRole] = {
    "folio.read": FolioRole.reader,
    "folio.create": FolioRole.creator,
    "folio.admin": FolioRole.admin,
}


class FolioAuthz:
    app = "folio"

    async def check(
        self, db: AsyncSession, user: User, permission: str | None, resource: Any
    ) -> Decision:
        role = await roles.effective_role(db, user)
        if role is None:
            return Decision(
                allowed=False,
                reason="You have no access to Folio. A Folio admin can give you a role in "
                "Admin, Global roles.",
                status=404,
                code="folio_no_access",
            )
        need = NEEDS.get(permission or "folio.read")
        if need is None:
            return Decision(
                allowed=False,
                reason=f"Unknown Folio permission '{permission}'.",
                status=403,
                code="unknown_permission",
            )
        if ROLE_RANK[role] < ROLE_RANK[need]:
            return Decision(
                allowed=False,
                reason=f"Your Folio role is {role.value}; this needs {need.value}. A Folio admin "
                "can change it in Admin, Global roles.",
                status=403,
                code="insufficient_role",
            )
        return Decision.allow()

    def visible_clause(self, user: User, model: Any) -> ColumnElement[bool]:
        return false()  # nothing to list until spaces and pages exist (phase 1)
