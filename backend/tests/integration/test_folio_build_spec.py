"""Build spec to tickets (Folio 4.3), at the service level. Acceptance: a phase's build
spec gives one task per deliverable with its criteria as a checklist, and running it again
only creates the new ones."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.models import FolioNode
from radicle.folio.services import build_spec
from radicle.platform.errors import Forbidden, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA
from tests.integration.test_docket_public import _user

SPEC = """# Fase 4

## Entregables

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 4.1 | Tickets dentro de los docs | Smart links | Veo su estado; PA-4 muestra el doc |
| 4.2 | Crear ticket desde texto | Selección | El ticket liga a la sección |
"""


async def write(client: AsyncClient, team: Team, node_id: uuid.UUID, md: str) -> None:
    r = await client.put(
        f"{API}/nodes/{node_id}/draft",
        headers=team.instance.headers,
        json={"content_md": md, "metadata": METADATA | {"doc_type": "build-spec"}},
    )
    assert r.status_code == 200, r.text


@pytest.fixture
async def spec(client: AsyncClient, db: AsyncSession, board: Team) -> FolioNode:
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Fase 4"}
    )
    node = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert node is not None
    await write(client, board, node.id, SPEC)
    return node


async def test_acceptance_one_task_per_deliverable(
    client: AsyncClient, db: AsyncSession, board: Team, spec: FolioNode
) -> None:
    fernando = await _user(db, board.instance.handle)
    found = await build_spec.items(db, fernando, spec)
    assert [(f.item.key, f.linked) for f in found] == [("4.1", False), ("4.2", False)]

    choice = build_spec.Choice(project="PA", milestone="V1", area="Backend")
    preview = await build_spec.create_tickets(db, fernando, spec, choice, dry_run=True)
    assert [p.item.key for p in preview] == ["4.1", "4.2"] and not any(p.ticket for p in preview)
    assert not any(f.linked for f in await build_spec.items(db, fernando, spec))

    made = await build_spec.create_tickets(db, fernando, spec, choice)
    assert [m.ticket.title for m in made if m.ticket] == [
        "4.1 Tickets dentro de los docs",
        "4.2 Crear ticket desde texto",
    ]
    first = made[0].ticket
    assert first is not None
    assert (first.type, first.milestone, first.area) == ("task", "V1", "Backend")
    assert (first.checklist_done, first.checklist_total) == (0, 2)
    seen = await docket.get_tickets(db, [first.key], fernando)
    assert seen[first.key] is not None

    # Again: nothing new. A new deliverable: only that one.
    assert await build_spec.create_tickets(db, fernando, spec, choice) == []
    await write(
        client, board, spec.id, SPEC + "| 4.3 | Build spec a tickets | Asistente | Sale |\n"
    )
    again = await build_spec.create_tickets(db, fernando, spec, choice)
    assert [a.item.key for a in again] == ["4.3"]
    found = await build_spec.items(db, fernando, spec)
    assert all(f.linked and f.ticket for f in found)


async def test_choosing_deliverables(db: AsyncSession, board: Team, spec: FolioNode) -> None:
    fernando = await _user(db, board.instance.handle)
    choice = build_spec.Choice(project="PA", keys=["4.2"], area="Backend")
    made = await build_spec.create_tickets(db, fernando, spec, choice)
    assert [m.item.key for m in made] == ["4.2"]
    assert made[0].ticket and "Fase 4 — Crear ticket desde texto" in build_spec.description(
        spec, made[0].item
    )
    with pytest.raises(ValidationFailed, match="Unknown deliverables: 9"):
        await build_spec.create_tickets(
            db, fernando, spec, build_spec.Choice(project="PA", keys=["9"])
        )


async def test_errors_and_permissions(
    client: AsyncClient, db: AsyncSession, board: Team, spec: FolioNode
) -> None:
    luis = await _user(db, board.member.handle)
    with pytest.raises(Forbidden):
        await build_spec.create_tickets(db, luis, spec, build_spec.Choice(project="PA"))
    fernando = await _user(db, board.instance.handle)
    r = await client.put(
        f"{API}/nodes/{spec.id}/draft",
        headers=board.instance.headers,
        json={"content_md": SPEC, "metadata": METADATA},
    )
    assert r.status_code == 200, r.text
    with pytest.raises(ValidationFailed, match="only build-spec docs"):
        await build_spec.items(db, fernando, spec)
