"""Retrieval for the docs chat (Folio 4.5): sections, not pages; the reader's visibility;
filters; and the re-ranking."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioSpace
from radicle.folio.services import retrieval, search
from tests.conftest import Team, run_jobs
from tests.integration.folio_chat_helpers import docs, user
from tests.integration.folio_helpers import API

__all__ = ["docs"]  # fixture


async def test_the_right_section_comes_first(db: AsyncSession, team: Team, docs: dict) -> None:
    member = await user(db, team.member.handle)
    found = await retrieval.retrieve(db, member, "¿Cómo conecto un agente?")
    assert str(found[0].node_id) == docs["guide"] and found[0].anchor == "conecta-un-agente"
    assert found[0].section == "Conecta un agente" and found[0].version == 1


async def test_never_hands_the_model_a_restricted_section(
    client: AsyncClient, db: AsyncSession, team: Team, docs: dict
) -> None:
    r = await client.put(
        f"{API}/nodes/{docs['guide']}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": "fernando"}]},
    )
    assert r.status_code == 200
    await run_jobs(db)
    member = await user(db, team.member.handle)
    found = await retrieval.retrieve(db, member, "conecta un agente con su token por MCP")
    assert docs["guide"] not in {str(p.node_id) for p in found}
    admin = await user(db, team.instance.handle)
    found = await retrieval.retrieve(db, admin, "conecta un agente con su token por MCP")
    assert str(found[0].node_id) == docs["guide"]


async def test_filters_narrow_the_passages(db: AsyncSession, team: Team, docs: dict) -> None:
    member = await user(db, team.member.handle)
    found = await retrieval.retrieve(
        db, member, "agente docker", filters=search.Filters(doc_type="guide")
    )
    assert {str(p.node_id) for p in found} == {docs["deploy"]}


async def test_a_space_with_its_ai_off_stays_out(db: AsyncSession, team: Team, docs: dict) -> None:
    space = await db.scalar(select(FolioSpace).where(FolioSpace.key == "docs"))
    assert space is not None
    space.ai_enabled = False
    await db.flush()
    admin = await user(db, team.instance.handle)
    assert await retrieval.retrieve(db, admin, "¿Cómo conecto un agente?") == []


def _p(node: uuid.UUID, chunk: int, score: float, section: str = "", status: str = "") -> object:
    return retrieval.Passage(
        chunk, node, 1, None, "Guía", section, "", "", "docs", status or "published", None, score
    )


def test_rerank_boosts_headings_and_caps_each_page() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    passages = [_p(a, n, 1.0) for n in range(1, 6)] + [_p(b, 9, 0.9, "Conecta un agente")]
    ranked = retrieval.rerank("conecta un agente", passages)  # type: ignore[arg-type]
    assert ranked[0].chunk_id == 9 and [p.node_id for p in ranked].count(a) == 3
    stale = [_p(a, 1, 1.0, status="outdated"), _p(b, 2, 0.9, status="verified")]
    assert [p.chunk_id for p in retrieval.rerank("x", stale)] == [2, 1]  # type: ignore[arg-type]
