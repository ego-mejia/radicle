from uuid import UUID

from fastapi import APIRouter, Response

from radicle.api.deps import CurrentPrincipal, Db, HumanUser
from radicle.api.schemas import MeOut, MePatch, Page, TokenCreate, TokenCreated, TokenOut
from radicle.core.errors import ValidationFailed
from radicle.services import auth, users

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(principal: CurrentPrincipal) -> MeOut:
    """Current user or agent and the projects they belong to, with role."""
    return MeOut.model_validate(principal.user)


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
    return MeOut.model_validate(user)


@router.get("/tokens", response_model=Page[TokenOut])
async def list_my_tokens(user: HumanUser, db: Db) -> Page[TokenOut]:
    tokens = await auth.list_tokens(db, user)
    return Page(items=[TokenOut.model_validate(t) for t in tokens])


@router.post("/tokens", response_model=TokenCreated, status_code=201)
async def create_my_token(body: TokenCreate, user: HumanUser, db: Db) -> TokenCreated:
    """Create a personal token. Its value is returned only in this response."""
    issued = await auth.issue_token(db, user, body.name, body.expires_at)
    return TokenCreated.from_issued(issued)


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_my_token(token_id: UUID, user: HumanUser, db: Db) -> Response:
    await auth.revoke_token(db, user, token_id)
    return Response(status_code=204)
