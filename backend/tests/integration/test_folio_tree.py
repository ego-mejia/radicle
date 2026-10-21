"""Folio spaces and the tree (Folio 1.1), through the services."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNodeEvent, NodeKind
from radicle.folio.services import nodes, spaces
from radicle.folio.services.nodes import NodeChanges, TreeNode
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed
from tests.conftest import Team


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


def shape(level: list[TreeNode]) -> list:
    return [(t.node.title, shape(t.children)) if t.children else t.node.title for t in level]


@pytest.fixture
async def admin(db: AsyncSession, team: Team) -> User:
    return await _user(db, team.instance.handle)


async def test_acceptance_ai_tools_space(db: AsyncSession, admin: User) -> None:
    space = await spaces.create_space(db, admin, key="ai-tools", name="AI Tools")
    folder = await nodes.create_node(db, admin, space, kind=NodeKind.folder, title="Get Started")
    one = await nodes.create_node(
        db, admin, space, kind=NodeKind.page, title="Bienvenido", parent_id=folder.id
    )
    two = await nodes.create_node(
        db, admin, space, kind=NodeKind.page, title="Conecta un agente", parent_id=one.id
    )
    await nodes.create_node(
        db, admin, space, kind=NodeKind.page, title="Crea el token", parent_id=two.id
    )
    post = await nodes.create_node(db, admin, space, kind=NodeKind.blog_post, title="Hola")

    assert shape(await nodes.tree(db, admin, space)) == [
        ("Get Started", [("Bienvenido", [("Conecta un agente", ["Crea el token"])])])
    ]
    assert [p.id for p in await nodes.posts(db, admin, space)] == [post.id]
    assert two.slug == "conecta-un-agente"
    assert [b.title for b in await nodes.breadcrumbs(db, two)] == ["Get Started", "Bienvenido"]


async def test_order_move_and_no_cycles(db: AsyncSession, admin: User) -> None:
    space = await spaces.create_space(db, admin, key="eng", name="Ingeniería")
    a, b, c = [
        await nodes.create_node(db, admin, space, kind=NodeKind.page, title=t) for t in "ABC"
    ]
    assert shape(await nodes.tree(db, admin, space)) == ["A", "B", "C"]
    await nodes.move_node(db, admin, c, parent_id=None, before_id=a.id)
    assert shape(await nodes.tree(db, admin, space)) == ["C", "A", "B"]
    await nodes.move_node(db, admin, a, parent_id=None, after_id=b.id)
    assert shape(await nodes.tree(db, admin, space)) == ["C", "B", "A"]
    await nodes.move_node(db, admin, b, parent_id=c.id)
    assert shape(await nodes.tree(db, admin, space)) == [("C", ["B"]), "A"]

    with pytest.raises(ValidationFailed, match="under itself"):
        await nodes.move_node(db, admin, c, parent_id=b.id)
    with pytest.raises(ValidationFailed, match="not a sibling"):
        await nodes.move_node(db, admin, a, parent_id=None, before_id=b.id)
    events = await db.scalars(
        select(FolioNodeEvent.event_type).where(FolioNodeEvent.node_id == b.id)
    )
    assert list(events) == ["created", "moved"]


async def test_soft_delete_hides_descendants(db: AsyncSession, admin: User) -> None:
    space = await spaces.create_space(db, admin, key="docs", name="Docs")
    parent = await nodes.create_node(db, admin, space, kind=NodeKind.page, title="Padre")
    child = await nodes.create_node(
        db, admin, space, kind=NodeKind.page, title="Hija", parent_id=parent.id
    )
    await nodes.delete_node(db, admin, parent)
    assert await nodes.tree(db, admin, space) == []
    with pytest.raises(NotFound):
        await nodes.get_node(db, admin, child.id)
    with pytest.raises(ValidationFailed, match="not a page or folder"):
        await nodes.create_node(
            db, admin, space, kind=NodeKind.page, title="Nieta", parent_id=child.id
        )


async def test_blog_posts_stay_out_of_the_tree(db: AsyncSession, admin: User) -> None:
    space = await spaces.create_space(db, admin, key="blog", name="Blog")
    post = await nodes.create_node(db, admin, space, kind=NodeKind.blog_post, title="Post")
    with pytest.raises(ValidationFailed, match="outside the tree"):
        await nodes.create_node(
            db, admin, space, kind=NodeKind.blog_post, title="X", parent_id=post.id
        )
    with pytest.raises(ValidationFailed, match="cannot have children"):
        await nodes.create_node(db, admin, space, kind=NodeKind.page, title="X", parent_id=post.id)
    with pytest.raises(ValidationFailed, match="cannot be moved"):
        await nodes.move_node(db, admin, post, parent_id=None)


async def test_rename_updates_the_slug_and_history_is_append_only(
    db: AsyncSession, admin: User
) -> None:
    space = await spaces.create_space(db, admin, key="ops", name="Ops")
    page = await nodes.create_node(db, admin, space, kind=NodeKind.page, title="Guía vieja")
    await nodes.update_node(db, admin, page, NodeChanges(title="Guía de deploy", icon="rocket"))
    assert page.slug == "guia-de-deploy" and page.icon == "rocket"
    with pytest.raises(ValidationFailed, match="1 to 200"):
        await nodes.update_node(db, admin, page, NodeChanges(title=" "))
    await db.flush()
    with pytest.raises(DBAPIError, match="append-only"):
        await db.execute(text("UPDATE folio_node_events SET event_type = 'x'"))


def test_slugify() -> None:
    assert nodes.slugify("¿Cómo conecto un agente?") == "como-conecto-un-agente"
    assert nodes.slugify("!!!") == "page"
    assert len(nodes.slugify("a" * 300)) == 60
