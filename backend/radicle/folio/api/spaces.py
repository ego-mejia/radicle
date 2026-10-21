"""Spaces and their tree over REST (Folio 1.1): /api/v1/folio/spaces, /nodes."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.db.models import FolioDraft, FolioNode, FolioSpace, NodeKind, SpacePermission
from radicle.folio.services import access, copying, nodes, publishing, social, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])

Kind = Literal["page", "folder", "blog_post", "live_doc", "database", "whiteboard"]


class SpaceOut(Output):
    id: uuid.UUID = Field(description="For follow and favorite (/watch/space/{id})")
    key: str
    name: str
    description: str
    kind: Literal["team", "personal"]
    icon: str | None
    cover_asset_id: uuid.UUID | None
    created_at: UtcDatetime
    permissions: list[str] = Field(description="What you may do here: view, create, ...")
    verify_days: int = Field(description="Days a Verified page stays verified")
    ai_enabled: bool = Field(description="False when the space admin turned the editor AI off")


class SpaceIn(Input):
    key: str = Field(description="2 to 40 lowercase letters, digits and dashes, e.g. ai-tools")
    name: str
    description: str = ""
    icon: str | None = None


class SpacePatch(Input):
    name: str | None = None
    description: str | None = None
    icon: str | None = Field(default=None, description="null removes it")
    verify_days: int | None = Field(
        default=None, description="Days a Verified page stays verified (1 to 730)"
    )
    ai_enabled: bool | None = Field(default=None, description="Turn the editor AI on or off")


class NodeRef(Output):
    id: uuid.UUID
    kind: Kind
    title: str
    slug: str
    icon: str | None
    status: Literal["draft", "published", "in_review", "verified", "outdated"]


class TreeItem(NodeRef):
    can_delete: bool = Field(
        description="You may archive it, delete it or move it to another space"
    )
    children: list["TreeItem"]


class NodeOut(NodeRef):
    space: str
    parent_id: uuid.UUID | None
    cover_asset_id: uuid.UUID | None
    published_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    breadcrumbs: list[NodeRef] = Field(description="Ancestors from the root down")
    version: int | None = Field(description="Published version; null until first published")
    metadata: dict[str, Any] | None = Field(description="Of the published version")
    content_json: dict[str, Any] | None = Field(description="Published content (TipTap)")
    verified_until: date | None
    archived_at: UtcDatetime | None
    can_edit: bool = Field(description="You may edit its draft (space and page restrictions)")
    can_delete: bool = Field(description="You may delete, archive or move it to another space")


class NodeIn(Input):
    space: str = Field(description="Space key")
    kind: Kind
    title: str
    parent: uuid.UUID | None = Field(default=None, description="Page or folder; never for posts")


class NodePatch(Input):
    title: str | None = None
    icon: str | None = Field(default=None, description="null removes it")
    cover_asset_id: uuid.UUID | None = Field(default=None, description="null removes it")


class NodeMoveIn(Input):
    space: str | None = Field(default=None, description="Another space's key to move it there")
    parent: uuid.UUID | None = Field(default=None, description="null moves it to the root")
    before: uuid.UUID | None = Field(default=None, description="Sibling to place it before")
    after: uuid.UUID | None = Field(default=None, description="Sibling to place it after")


async def _space(db: Db, user: User, s: FolioSpace) -> SpaceOut:
    granted = await access.space_permissions(db, user, s)
    return SpaceOut(
        id=s.id,
        permissions=[p.value for p in SpacePermission if p.value in granted],
        key=s.key,
        name=s.name,
        description=s.description,
        kind=s.kind.value,
        icon=s.icon,
        cover_asset_id=s.cover_asset_id,
        created_at=s.created_at,
        verify_days=s.verify_days,
        ai_enabled=s.ai_enabled,
    )


def _ref(n: FolioNode) -> NodeRef:
    return NodeRef(
        id=n.id, kind=n.kind.value, title=n.title, slug=n.slug, icon=n.icon, status=n.status.value
    )


def _tree(level: list[nodes.TreeNode], perms: frozenset[str], user: User) -> list[TreeItem]:
    """The tree, each item saying whether you may delete it (the space's permissions, which
    are the same for every node, plus delete_own for your own)."""

    def deletable(node: FolioNode) -> bool:
        return "delete_any" in perms or ("delete_own" in perms and node.created_by == user.id)

    return [
        TreeItem(
            **_ref(t.node).model_dump(),
            can_delete=deletable(t.node),
            children=_tree(t.children, perms, user),
        )
        for t in level
    ]


async def _content(db: Db, node: FolioNode, current: Any) -> dict[str, Any] | None:
    """The published content; for a live doc, what it says right now (Folio 2.5)."""
    if node.kind == NodeKind.live_doc:
        draft = await db.get(FolioDraft, node.id)
        return draft.content_json if draft is not None else None
    return current.content_json if current is not None else None


async def _node(db: Db, user: User, node: FolioNode) -> NodeOut:
    space = await db.get(FolioSpace, node.space_id)
    current = await publishing.current_version(db, node)
    return NodeOut(
        **_ref(node).model_dump(),
        space=space.key if space else "",
        parent_id=node.parent_id,
        cover_asset_id=node.cover_asset_id,
        published_at=node.published_at,
        created_at=node.created_at,
        updated_at=node.updated_at,
        breadcrumbs=[_ref(b) for b in await nodes.breadcrumbs(db, node)],
        version=current.number if current else None,
        metadata=current.metadata_ if current else None,
        content_json=await _content(db, node, current),
        verified_until=node.verified_until,
        archived_at=node.archived_at,
        can_edit=await access.may_edit(db, user, node),
        can_delete=await access.may_delete(db, user, node),
    )


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/spaces", response_model=Page[SpaceOut])
async def list_spaces(principal: CurrentPrincipal, db: Db) -> Page[SpaceOut]:
    """Team spaces you can see, then your personal space."""
    await _reader(db, principal)
    return Page(
        items=[
            await _space(db, principal.user, s)
            for s in await spaces.list_spaces(db, principal.user)
        ]
    )


@router.post("/spaces", response_model=SpaceOut, status_code=201)
async def create_space(body: SpaceIn, principal: CurrentPrincipal, db: Db) -> SpaceOut:
    """A team space (Folio creators and admins)."""
    space = await spaces.create_space(
        db,
        principal.user,
        key=body.key,
        name=body.name,
        description=body.description,
        icon=body.icon,
    )
    return await _space(db, principal.user, space)


@router.get("/me/personal-space", response_model=SpaceOut)
async def my_space(principal: CurrentPrincipal, db: Db) -> SpaceOut:
    """Your personal space, created the first time you ask for it."""
    await _reader(db, principal)
    return await _space(db, principal.user, await spaces.personal_space(db, principal.user))


@router.get("/spaces/{key}", response_model=SpaceOut)
async def get_space(key: str, principal: CurrentPrincipal, db: Db) -> SpaceOut:
    await _reader(db, principal)
    return await _space(db, principal.user, await spaces.get_space(db, principal.user, key))


@router.patch("/spaces/{key}", response_model=SpaceOut)
async def patch_space(key: str, body: SpacePatch, principal: CurrentPrincipal, db: Db) -> SpaceOut:
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    changes = spaces.SpaceChanges(
        name=body.name,
        description=body.description,
        icon=body.icon,
        clear_icon="icon" in body.model_fields_set and body.icon is None,
        verify_days=body.verify_days,
        ai_enabled=body.ai_enabled,
    )
    return await _space(
        db, principal.user, await spaces.update_space(db, principal.user, space, changes)
    )


@router.delete("/spaces/{key}", status_code=204)
async def delete_space(key: str, principal: CurrentPrincipal, db: Db) -> Response:
    """Soft delete: the space and its pages disappear; their history stays."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    await spaces.delete_space(db, principal.user, space)
    return Response(status_code=204)


@router.get("/spaces/{key}/tree", response_model=list[TreeItem])
async def get_tree(key: str, principal: CurrentPrincipal, db: Db) -> list[TreeItem]:
    """Pages and folders as a tree, siblings in order. Blog posts are under /posts."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    perms = await access.space_permissions(db, principal.user, space)
    return _tree(await nodes.tree(db, principal.user, space), perms, principal.user)


@router.get("/spaces/{key}/posts", response_model=Page[NodeRef])
async def list_posts(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    before: datetime | None = Query(default=None, description="Posts older than this"),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[NodeRef]:
    """Blog posts, newest first."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    return Page(
        items=[
            _ref(p)
            for p in await nodes.posts(db, principal.user, space, before=before, limit=limit)
        ]
    )


@router.post("/nodes", response_model=NodeOut, status_code=201)
async def create_node(body: NodeIn, principal: CurrentPrincipal, db: Db) -> NodeOut:
    """A page or folder (optionally under `parent`) or a blog post."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, body.space)
    node = await nodes.create_node(
        db, principal.user, space, kind=NodeKind(body.kind), title=body.title, parent_id=body.parent
    )
    return await _node(db, principal.user, node)


@router.get("/nodes/{node_id}", response_model=NodeOut)
async def get_node(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> NodeOut:
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    await social.record_view(db, principal.user, node)
    return await _node(db, principal.user, node)


@router.patch("/nodes/{node_id}", response_model=NodeOut)
async def patch_node(
    node_id: uuid.UUID, body: NodePatch, principal: CurrentPrincipal, db: Db
) -> NodeOut:
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    sent = body.model_fields_set
    changes = nodes.NodeChanges(
        title=body.title,
        icon=body.icon,
        clear_icon="icon" in sent and body.icon is None,
        cover_asset_id=body.cover_asset_id,
        clear_cover="cover_asset_id" in sent and body.cover_asset_id is None,
    )
    return await _node(
        db, principal.user, await nodes.update_node(db, principal.user, node, changes)
    )


@router.post("/nodes/{node_id}/move", response_model=NodeOut)
async def move_node(
    node_id: uuid.UUID, body: NodeMoveIn, principal: CurrentPrincipal, db: Db
) -> NodeOut:
    """Move within its space (`before` and `after` place it among its new siblings), or to
    another `space`, which takes delete here and create there; id, URL, history and
    restrictions stay."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    if body.space is not None:
        target = await spaces.get_space(db, principal.user, body.space)
        if target.id != node.space_id:
            moved = await copying.move_to_space(
                db, principal.user, node, target, parent_id=body.parent
            )
            return await _node(db, principal.user, moved)
    moved = await nodes.move_node(
        db, principal.user, node, parent_id=body.parent, before_id=body.before, after_id=body.after
    )
    return await _node(db, principal.user, moved)


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """Soft delete; its children go with it."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    await nodes.delete_node(db, principal.user, node)
    return Response(status_code=204)
