from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.api.deps import CurrentPrincipal, Db, HumanUser
from radicle.api.schemas.common import Page
from radicle.api.schemas.users import (
    MeOut,
    MePatch,
    MeProject,
    TokenCreate,
    TokenCreated,
    TokenOut,
    UserOut,
)
from radicle.core.permissions import permissions_for
from radicle.db.models import User
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import audit, auth, users
from radicle.services import projects

router = APIRouter(prefix="/me", tags=["me"])


async def me_out(db: AsyncSession, user: User) -> MeOut:
    rows = await projects.list_projects(db, user)
    base = UserOut.model_validate(user).model_dump()
    return MeOut(
        **base,
        projects=[
            MeProject(
                key=r.project.key,
                name=r.project.name,
                role=r.role,
                permissions=sorted(await permissions_for(db, r.project, r.role)),
            )
            for r in rows
        ],
    )


@router.get("", response_model=MeOut)
async def get_me(principal: CurrentPrincipal, db: Db) -> MeOut:
    """Current user or agent and the projects they belong to, with role."""
    return await me_out(db, principal.user)


@router.patch("", response_model=MeOut)
async def patch_me(body: MePatch, user: HumanUser, db: Db) -> MeOut:
    if body.new_password is not None:
        if body.current_password is None:
            raise ValidationFailed(
                "Send current_password to set a new password.",
                errors=[{"field": "current_password", "message": "required"}],
            )
        await users.change_own_password(
            db, user, current_password=body.current_password, new_password=body.new_password
        )
    if body.display_name is not None:
        await users.update_user(db, user, users.UserChanges(display_name=body.display_name))
    return await me_out(db, user)


@router.get("/tokens", response_model=Page[TokenOut])
async def list_my_tokens(user: HumanUser, db: Db) -> Page[TokenOut]:
    tokens = await auth.list_tokens(db, user)
    return Page(items=[TokenOut.model_validate(t) for t in tokens])


@router.post("/tokens", response_model=TokenCreated, status_code=201)
async def create_my_token(body: TokenCreate, user: HumanUser, db: Db) -> TokenCreated:
    """Create a personal token. Its value is returned only in this response."""
    issued = await auth.issue_token(db, user, body.name, body.expires_at)
    audit.record(
        db,
        user,
        "token.create",
        target_type="token",
        target_id=issued.record.id,
        owner=user.handle,
        name=body.name,
    )
    return TokenCreated.from_issued(issued)


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_my_token(token_id: UUID, user: HumanUser, db: Db) -> Response:
    await auth.revoke_token(db, user, token_id)
    audit.record(
        db, user, "token.revoke", target_type="token", target_id=token_id, owner=user.handle
    )
    return Response(status_code=204)
