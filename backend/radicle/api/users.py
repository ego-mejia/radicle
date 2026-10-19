from uuid import UUID

from fastapi import APIRouter, Response

from radicle.api.deps import AppSettings, Db, InstanceAdmin
from radicle.api.pagination import DEFAULT_LIMIT, Limit, decode_cursor, encode_cursor
from radicle.api.schemas import (
    AgentCreate,
    AgentCreated,
    Page,
    TokenCreate,
    TokenCreated,
    TokenOut,
    UserCreate,
    UserOut,
    UserPatch,
)
from radicle.core.errors import ValidationFailed
from radicle.db.models import UserKind
from radicle.services import auth, users

router = APIRouter(tags=["users"])


def _token_created(issued: auth.IssuedToken) -> TokenCreated:
    return TokenCreated.from_issued(issued)


@router.get("/users", response_model=Page[UserOut])
async def list_users(
    _: InstanceAdmin, db: Db, limit: Limit = DEFAULT_LIMIT, cursor: str | None = None
) -> Page[UserOut]:
    """Humans and agents, oldest first."""
    rows = await users.list_users(db, limit=limit + 1, after=decode_cursor(cursor))
    page, more = rows[:limit], len(rows) > limit
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if more else None
    return Page(items=[UserOut.model_validate(u) for u in page], next_cursor=next_cursor)


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, _: InstanceAdmin, db: Db) -> UserOut:
    user = await users.create_human(
        db,
        handle=body.handle,
        display_name=body.display_name,
        email=str(body.email),
        password=body.password,
        is_instance_admin=body.is_instance_admin,
    )
    return UserOut.model_validate(user)


@router.post("/agents", response_model=AgentCreated, status_code=201)
async def create_agent(
    body: AgentCreate, _: InstanceAdmin, db: Db, settings: AppSettings
) -> AgentCreated:
    """Create an agent and its first token. The token value is returned only here."""
    agent, issued = await users.create_agent(
        db, handle=body.handle, display_name=body.display_name, token_name=body.token_name
    )
    return AgentCreated(
        agent=UserOut.model_validate(agent),
        token=_token_created(issued),
        mcp_url=settings.base_url.rstrip("/") + "/mcp",
    )


@router.get("/users/{handle}", response_model=UserOut)
async def get_user(handle: str, _: InstanceAdmin, db: Db) -> UserOut:
    return UserOut.model_validate(await users.get_by_handle(db, handle))


@router.patch("/users/{handle}", response_model=UserOut)
async def patch_user(handle: str, body: UserPatch, _: InstanceAdmin, db: Db) -> UserOut:
    user = await users.get_by_handle(db, handle)
    changes = users.UserChanges(
        display_name=body.display_name,
        email=str(body.email) if body.email is not None else None,
        password=body.password,
        is_active=body.is_active,
        is_instance_admin=body.is_instance_admin,
    )
    return UserOut.model_validate(await users.update_user(db, user, changes))


@router.get("/users/{handle}/tokens", response_model=Page[TokenOut])
async def list_user_tokens(handle: str, _: InstanceAdmin, db: Db) -> Page[TokenOut]:
    user = await users.get_by_handle(db, handle)
    return Page(items=[TokenOut.model_validate(t) for t in await auth.list_tokens(db, user)])


@router.post("/users/{handle}/tokens", response_model=TokenCreated, status_code=201)
async def create_agent_token(
    handle: str, body: TokenCreate, _: InstanceAdmin, db: Db
) -> TokenCreated:
    """New token for an agent. Humans create their own tokens from /me/tokens."""
    user = await users.get_by_handle(db, handle)
    if user.kind is not UserKind.agent:
        raise ValidationFailed(
            f"@{user.handle} is a human; personal tokens are created by their owner at /me/tokens.",
            code="not_an_agent",
        )
    return _token_created(await auth.issue_token(db, user, body.name, body.expires_at))


@router.delete("/users/{handle}/tokens/{token_id}", status_code=204)
async def revoke_user_token(handle: str, token_id: UUID, _: InstanceAdmin, db: Db) -> Response:
    user = await users.get_by_handle(db, handle)
    await auth.revoke_token(db, user, token_id)
    return Response(status_code=204)
