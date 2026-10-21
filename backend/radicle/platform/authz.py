"""One authorization entry point for every app (ADR 0035). Each app registers a provider
that knows its own rules; platform only routes the question and fails closed."""

from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import ColumnElement, false
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound, ProblemError


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""
    # When denied: 404 hides that the resource exists, 403 says it exists but is off-limits.
    status: int = 403
    code: str = "forbidden"

    @classmethod
    def allow(cls) -> "Decision":
        return cls(allowed=True)

    @classmethod
    def deny(cls, error: ProblemError) -> "Decision":
        return cls(allowed=False, reason=error.detail, status=error.status, code=error.code)

    def raise_if_denied(self) -> None:
        if self.allowed:
            return
        kind = NotFound if self.status == 404 else Forbidden
        raise kind(self.reason, code=self.code)


class AuthzProvider(Protocol):
    app: str

    async def check(
        self, db: AsyncSession, user: User, permission: str | None, resource: Any
    ) -> Decision: ...

    def visible_clause(self, user: User, model: Any) -> ColumnElement[bool]: ...


_providers: dict[str, AuthzProvider] = {}


def register(provider: AuthzProvider) -> None:
    _providers[provider.app] = provider


def unregister(app: str) -> None:
    _providers.pop(app, None)


def apps() -> tuple[str, ...]:
    return tuple(sorted(_providers))


def _unknown(app: str) -> Decision:
    known = ", ".join(apps()) or "none"
    return Decision(
        allowed=False,
        reason=f"Unknown app '{app}'. Registered apps: {known}.",
        status=404,
        code="unknown_app",
    )


async def authorize(
    db: AsyncSession, user: User, app: str, permission: str | None, resource: Any = None
) -> Decision:
    """Whether `user` may do `permission` on `resource` in `app`. Never raises for a denial;
    call `raise_if_denied()` on the result to turn it into the usual API error."""
    provider = _providers.get(app)
    if provider is None:
        return _unknown(app)
    return await provider.check(db, user, permission, resource)


def visible(user: User, app: str, model: Any) -> ColumnElement[bool]:
    """SQL filter for the rows of `model` the user may see; nothing for an unknown app."""
    provider = _providers.get(app)
    if provider is None:
        return false()
    return provider.visible_clause(user, model)
