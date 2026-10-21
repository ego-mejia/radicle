"""Templates (Folio 3.1). Acceptance: a build spec created from its template already has
its sections and metadata."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioDraft, FolioNode, FolioSpace
from radicle.folio.db.templates import FolioTemplate, TemplateKind
from radicle.folio.services import convert, quality, templates
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_helpers import API


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def space(client: AsyncClient, db: AsyncSession, team: Team) -> FolioSpace:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    found = await db.scalar(select(FolioSpace).where(FolioSpace.key == "eng"))
    assert found is not None
    return found


async def _builtin(db: AsyncSession, user: User, key: str) -> FolioTemplate:
    listed = await templates.list_templates(db, user)
    return next(t for t in listed if t.builtin_key == key)


async def test_the_included_templates_appear_once(db: AsyncSession, team: Team) -> None:
    fernando = await _user(db, team.instance.handle)
    first = await templates.list_templates(db, fernando)
    assert [t.builtin_key for t in first][:1] == ["build-spec"] or "build-spec" in {
        t.builtin_key for t in first
    }
    await templates.list_templates(db, fernando)
    count = await db.scalar(select(func.count()).select_from(FolioTemplate))
    assert count == len(first) == 6


async def test_acceptance_a_build_spec_from_its_template(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, team.instance.handle)
    spec = await _builtin(db, fernando, "build-spec")
    node = await templates.create_page(db, fernando, spec, space, title="Etapa 5: integraciones")
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None
    md = convert.to_markdown(draft.content_json)
    for section in ("## Objetivo y alcance", "## Entregables", "## Modelo de datos", "## Tests"):
        assert section in md
    assert f"{quality.today().isoformat()} · @{fernando.handle}" in md
    assert draft.metadata_["doc_type"] == "build-spec" and draft.metadata_["labels"] == ["spec"]
    assert draft.metadata_["owner"] == f"@{fernando.handle}"


async def test_variables_and_own_templates(db: AsyncSession, team: Team, space: FolioSpace) -> None:
    fernando = await _user(db, team.instance.handle)
    data = templates.TemplateData(
        kind=TemplateKind.page,
        name="Daily",
        content_md="# {{titulo}} en {{space}}\n\nPor {{author}} el {{date}}; {{otra}} queda.",
        default_metadata={"labels": ["daily"]},
    )
    template = await templates.create_template(db, fernando, data, space=space)
    node = await templates.create_page(db, fernando, template, space, title="Daily del lunes")
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None
    md = convert.to_markdown(draft.content_json)
    assert "# Daily del lunes en Ingeniería" in md and "{{otra}} queda" in md
    assert f"Por {fernando.handle} el {quality.today().isoformat()}" in md


async def test_a_space_from_a_template(db: AsyncSession, team: Team) -> None:
    fernando = await _user(db, team.instance.handle)
    data = templates.TemplateData(
        kind=TemplateKind.space,
        name="Equipo de producto",
        structure={
            "description": "Specs y decisiones.",
            "pages": [
                {
                    "title": "Specs",
                    "kind": "folder",
                    "children": [
                        {"title": "Spec de ejemplo", "template": "build-spec"},
                    ],
                },
                {"title": "Decisiones", "template": "decision-log"},
                {"title": "Notas"},
            ],
            "grants": [
                {"grantee_type": "user", "grantee": "ana", "permissions": ["view", "create"]}
            ],
        },
    )
    template = await templates.create_template(db, fernando, data)
    space = await templates.create_space(db, fernando, template, key="prod", name="Producto")
    rows = list(await db.scalars(select(FolioNode).where(FolioNode.space_id == space.id)))
    titles = {n.title: n for n in rows}
    assert set(titles) == {"Specs", "Spec de ejemplo", "Decisiones", "Notas"}
    assert titles["Spec de ejemplo"].parent_id == titles["Specs"].id
    spec_draft = await db.get(FolioDraft, titles["Spec de ejemplo"].id)
    assert spec_draft is not None and spec_draft.metadata_["doc_type"] == "build-spec"
    assert space.description == "Specs y decisiones."


async def test_permissions_and_errors(db: AsyncSession, team: Team, space: FolioSpace) -> None:
    luis = await _user(db, team.member.handle)
    data = templates.TemplateData(kind=TemplateKind.page, name="Mía", content_md="Hola")
    with pytest.raises(Forbidden):
        await templates.create_template(db, luis, data)  # global: Folio admins only
    with pytest.raises(Forbidden):
        await templates.create_template(db, luis, data, space=space)  # space admins only
    fernando = await _user(db, team.instance.handle)
    with pytest.raises(ValidationFailed):
        await templates.create_template(
            db, fernando, templates.TemplateData(kind=TemplateKind.page, name=" ")
        )
    bad = templates.TemplateData(
        kind=TemplateKind.space, name="Mala", structure={"pages": [{"kind": "page"}]}
    )
    with pytest.raises(ValidationFailed):
        await templates.create_template(db, fernando, bad)
    spec = await _builtin(db, fernando, "build-spec")
    with pytest.raises(ValidationFailed):
        await templates.create_space(db, fernando, spec, key="x", name="X")
