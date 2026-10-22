"""Docs linked to Docket tickets (Folio 4.1, 4.2), at the service level."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.docket_links import TicketLinkKind
from radicle.folio.db.models import FolioNode
from radicle.folio.services import ticket_links
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team, new_ticket
from tests.integration.folio_helpers import API, publish
from tests.integration.test_docket_public import _user
from tests.integration.test_restricted import restrict


@pytest.fixture
async def page(client: AsyncClient, db: AsyncSession, board: Team) -> FolioNode:
    """PA-1 and PA-2 (restricted) in Docket; a page in space eng that nobody linked yet."""
    await new_ticket(client, board.admin, title="Conectar agentes", assignee="luis")
    await new_ticket(client, board.admin, title="Secreto")
    r = await client.post(
        "/api/v1/projects/PA/security-levels",
        headers=board.admin.headers,
        json={"name": "Legal confidencial", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    assert (await restrict(client, board, "PA-2")).status_code == 200
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Guía"}
    )
    node = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert node is not None
    return node


async def test_publishing_records_the_tickets_a_doc_mentions(
    client: AsyncClient, db: AsyncSession, board: Team, page: FolioNode
) -> None:
    md = "# Conecta un agente\n\nVer PA-1, PA-2 y ZZ-9; no PA-1x ni XPA-1."
    await publish(client, board, str(page.id), md)
    fernando = await _user(db, "fernando")
    links = await ticket_links.links_for_node(db, fernando, page)
    assert sorted(lk.ticket.key for lk in links if lk.ticket) == ["PA-1", "PA-2"]
    assert {lk.link.kind for lk in links} == {TicketLinkKind.mention}
    # luis can't see PA-2: the link is there but restricted for him.
    luis = await _user(db, "luis")
    seen = {
        lk.ticket.key if lk.ticket else None
        for lk in await ticket_links.links_for_node(db, luis, page)
    }
    assert seen == {"PA-1", None}
    docs = await ticket_links.docs_for_ticket(db, luis, "pa-1")
    assert [d.node.id for d in docs] == [page.id] and docs[0].space_key == "eng"
    with pytest.raises(NotFound):
        await ticket_links.docs_for_ticket(db, luis, "PA-2")
    # Publishing again without the mention drops it.
    await publish(client, board, str(page.id), "Ya nada.")
    assert await ticket_links.links_for_node(db, fernando, page) == []


async def test_link_and_unlink_by_hand(db: AsyncSession, board: Team, page: FolioNode) -> None:
    fernando = await _user(db, "fernando")
    made = await ticket_links.link(db, fernando, page, "pa-1", anchor="conecta-un-agente")
    again = await ticket_links.link(db, fernando, page, "PA-1")
    assert made.link.id == again.link.id and made.link.anchor == "conecta-un-agente"
    assert made.ticket is not None and made.ticket.assignee_handle == "luis"
    with pytest.raises(ValidationFailed, match="heading anchor"):
        await ticket_links.link(db, fernando, page, "PA-1", anchor="Not An Anchor")
    with pytest.raises(NotFound, match="can't see it"):
        await ticket_links.link(db, fernando, page, "ZZ-9")
    with pytest.raises(Forbidden):
        await ticket_links.link(db, await _user(db, "luis"), page, "PA-1")
    with pytest.raises(NotFound):
        await ticket_links.unlink(db, fernando, page, uuid.uuid4())
    await ticket_links.unlink(db, fernando, page, made.link.id)
    await ticket_links.link(db, fernando, page, "PA-1")
    assert await ticket_links.unlink_key(db, fernando, page, "PA-1") == 1
    assert await ticket_links.links_for_node(db, fernando, page) == []


async def test_a_doc_shows_once_on_its_ticket(
    client: AsyncClient, db: AsyncSession, board: Team, page: FolioNode
) -> None:
    await publish(client, board, str(page.id), "# Conecta un agente\n\nVer PA-1.")
    fernando = await _user(db, "fernando")
    await ticket_links.link(db, fernando, page, "PA-1", anchor="conecta-un-agente")
    docs = await ticket_links.docs_for_ticket(db, fernando, "PA-1")
    assert [d.node.id for d in docs] == [page.id]
    assert docs[0].link.kind == TicketLinkKind.manual and docs[0].link.anchor == "conecta-un-agente"


async def test_create_a_ticket_from_a_selection(
    client: AsyncClient, db: AsyncSession, board: Team, page: FolioNode
) -> None:
    await publish(client, board, str(page.id), "# Conecta un agente\n\nCon su token.")
    luis = await _user(db, "luis")
    data = ticket_links.FromText(
        text="Documentar el token del agente\ncon un ejemplo",
        project="PA",
        anchor="conecta-un-agente",
        area="Backend",
    )
    made = await ticket_links.create_from_text(db, luis, page, data)
    assert made.ticket is not None and made.ticket.title == "Documentar el token del agente"
    assert made.link.kind == TicketLinkKind.created_from_text
    assert made.link.anchor == "conecta-un-agente"
    r = await client.get(f"/api/v1/tickets/{made.ticket.key}", headers=board.admin.headers)
    # The page is in Spanish, so the ticket's own words are too.
    assert "Del documento [" in r.json()["description_md"]
    long = ticket_links.FromText(text="x" * 300, project="PA", area="Backend")
    assert len((await ticket_links.create_from_text(db, luis, page, long)).ticket.title) == 120  # type: ignore[union-attr]
    with pytest.raises(ValidationFailed, match="selected text"):
        await ticket_links.create_from_text(db, luis, page, ticket_links.FromText("  ", "PA"))
    with pytest.raises(Forbidden):
        await ticket_links.create_from_text(db, await _user(db, "vera"), page, data)


def test_keys_in_text() -> None:
    text = "PA-4 y RAD-38, otra vez PA-4; no a-1, PA-, XPA-1x ni PA-1-2."
    assert ticket_links.keys_in(text) == ["PA-4", "RAD-38"]
