from uuid import UUID

from fastapi import APIRouter, Response

from radicle.api.deps import AppSettings, Db, InstanceAdmin
from radicle.api.pagination import DEFAULT_LIMIT, Limit, decode_cursor, encode_cursor
from radicle.api.schemas.common import Page
from radicle.api.schemas.users import (
    AgentCreate,
    AgentCreated,
    McpToolOut,
    TokenCreate,
    TokenCreated,
    TokenOut,
    UserCreate,
    UserOut,
    UserPatch,
)
from radicle.core import mcp_catalog
from radicle.core.errors import ValidationFailed
from radicle.db.models import User, UserKind
from radicle.services import audit, auth, users

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
async def create_user(body: UserCreate, admin: InstanceAdmin, db: Db) -> UserOut:
    user = await users.create_human(
        db,
        handle=body.handle,
        display_name=body.display_name,
        email=str(body.email),
        password=body.password,
        is_instance_admin=body.is_instance_admin,
    )
    audit.record(
        db, admin, "user.create", target_type="user", target_id=user.handle, after=_user_view(user)
    )
    if user.is_instance_admin:
        audit.record(db, admin, "user.make_admin", target_type="user", target_id=user.handle)
    return UserOut.model_validate(user)


def _user_view(user: User) -> dict[str, object]:
    return {
        "handle": user.handle,
        "display_name": user.display_name,
        "email": user.email,
        "is_instance_admin": user.is_instance_admin,
        "is_active": user.is_active,
        "mcp_tools": user.mcp_tools,
    }


@router.post("/agents", response_model=AgentCreated, status_code=201)
async def create_agent(
    body: AgentCreate, admin: InstanceAdmin, db: Db, settings: AppSettings
) -> AgentCreated:
    """Create an agent and its first token. The token value is returned only here."""
    agent, issued = await users.create_agent(
        db,
        handle=body.handle,
        display_name=body.display_name,
        token_name=body.token_name,
        mcp_tools=body.mcp_tools,
    )
    audit.record(
        db,
        admin,
        "agent.create",
        target_type="user",
        target_id=agent.handle,
        after=_user_view(agent),
    )
    audit.record(
        db,
        admin,
        "token.create",
        target_type="token",
        target_id=issued.record.id,
        owner=agent.handle,
        name=body.token_name,
    )
    return AgentCreated(
        agent=UserOut.model_validate(agent),
        token=_token_created(issued),
        mcp_url=settings.base_url.rstrip("/") + "/mcp",
    )


@router.get("/mcp/tools", response_model=list[McpToolOut])
async def list_mcp_tools(_: InstanceAdmin) -> list[McpToolOut]:
    """Every MCP tool with its group, for choosing what an agent may call."""
    from radicle.mcp.server import server  # the MCP server mounts after the routers

    described = {tool.name: tool.description or "" for tool in await server.list_tools()}
    return [
        McpToolOut(
            name=name,
            group=mcp_catalog.GROUP_OF[name],
            read_only=name in mcp_catalog.READ_ONLY,
            description=described.get(name, ""),
        )
        for name in mcp_catalog.TOOLS
    ]


@router.get("/users/{handle}", response_model=UserOut)
async def get_user(handle: str, _: InstanceAdmin, db: Db) -> UserOut:
    return UserOut.model_validate(await users.get_by_handle(db, handle))


@router.patch("/users/{handle}", response_model=UserOut)
async def patch_user(handle: str, body: UserPatch, admin: InstanceAdmin, db: Db) -> UserOut:
    user = await users.get_by_handle(db, handle)
    before = _user_view(user)
    changes = users.UserChanges(
        display_name=body.display_name,
        email=str(body.email) if body.email is not None else None,
        password=body.password,
        is_active=body.is_active,
        is_instance_admin=body.is_instance_admin,
        set_mcp_tools="mcp_tools" in body.model_fields_set,
        mcp_tools=body.mcp_tools,
    )
    await users.update_user(db, user, changes)
    after = _user_view(user)
    kind = "agent.update" if user.kind is UserKind.agent else "user.update"
    audit.record(
        db,
        admin,
        kind,
        target_type="user",
        target_id=user.handle,
        before=before,
        after=after,
        password_changed=body.password is not None,
    )
    if before["is_active"] and not after["is_active"]:
        audit.record(db, admin, "user.deactivate", target_type="user", target_id=user.handle)
    if not before["is_instance_admin"] and after["is_instance_admin"]:
        audit.record(db, admin, "user.make_admin", target_type="user", target_id=user.handle)
    return UserOut.model_validate(user)


@router.get("/users/{handle}/tokens", response_model=Page[TokenOut])
async def list_user_tokens(handle: str, _: InstanceAdmin, db: Db) -> Page[TokenOut]:
    user = await users.get_by_handle(db, handle)
    return Page(items=[TokenOut.model_validate(t) for t in await auth.list_tokens(db, user)])


@router.post("/users/{handle}/tokens", response_model=TokenCreated, status_code=201)
async def create_agent_token(
    handle: str, body: TokenCreate, admin: InstanceAdmin, db: Db
) -> TokenCreated:
    """New token for an agent. Humans create their own tokens from /me/tokens."""
    user = await users.get_by_handle(db, handle)
    if user.kind is not UserKind.agent:
        raise ValidationFailed(
            f"@{user.handle} is a human; personal tokens are created by their owner at /me/tokens.",
            code="not_an_agent",
        )
    issued = await auth.issue_token(db, user, body.name, body.expires_at)
    audit.record(
        db,
        admin,
        "token.create",
        target_type="token",
        target_id=issued.record.id,
        owner=user.handle,
        name=body.name,
    )
    return _token_created(issued)


@router.delete("/users/{handle}/tokens/{token_id}", status_code=204)
async def revoke_user_token(handle: str, token_id: UUID, admin: InstanceAdmin, db: Db) -> Response:
    user = await users.get_by_handle(db, handle)
    await auth.revoke_token(db, user, token_id)
    audit.record(
        db, admin, "token.revoke", target_type="token", target_id=token_id, owner=user.handle
    )
    return Response(status_code=204)
