"""Publishing metadata (Folio 1.3): normalized when complete, every failing field otherwise."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import NodeKind
from radicle.folio.services import catalogs, nodes, spaces
from radicle.folio.services.metadata import MetadataIncomplete, validate_metadata
from radicle.platform.db.models import User
from tests.conftest import Team

GOOD = {
    "description": "Cómo conectar un agente a Radicle por MCP, paso a paso y con el token.",
    "doc_type": "how-to",
    "labels": ["mcp", "#Agentes", "mcp"],
    "owner": "@Fernando",
    "audiences": ["everyone"],
    "language": "es",
}


@pytest.fixture
async def node(db: AsyncSession, team: Team):  # type: ignore[no-untyped-def]
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    space = await spaces.create_space(db, admin, key="docs", name="Docs")
    return await nodes.create_node(db, admin, space, kind=NodeKind.page, title="Conecta")


async def test_complete_metadata_is_normalized(db: AsyncSession, node) -> None:  # type: ignore[no-untyped-def]
    out = await validate_metadata(db, node, GOOD)
    assert out["title"] == "Conecta"  # the node's title when the draft has none
    assert out["labels"] == ["mcp", "agentes"] and out["owner"] == "fernando"
    assert (await validate_metadata(db, node, GOOD | {"title": " Otro "}))["title"] == "Otro"


async def errors(db: AsyncSession, node, metadata: dict) -> list[dict]:  # type: ignore[no-untyped-def]
    with pytest.raises(MetadataIncomplete) as exc:
        await validate_metadata(db, node, metadata)
    assert exc.value.status == 422 and "metadata-schema" in exc.value.detail
    return exc.value.errors


async def test_every_missing_field_is_listed(db: AsyncSession, node) -> None:  # type: ignore[no-untyped-def]
    fields = [e["field"] for e in await errors(db, node, {})]
    assert fields == ["description", "doc_type", "labels", "owner", "audiences", "language"]


async def test_invalid_values(db: AsyncSession, node, team: Team) -> None:  # type: ignore[no-untyped-def]
    bad = GOOD | {
        "doc_type": "poema",
        "labels": ["Con Espacios"],
        "audiences": ["marte"],
        "description": "Corta.",
        "owner": team.agent.handle,
        "language": "fr",
        "title": "x" * 201,
    }
    assert {e["field"] for e in await errors(db, node, bad)} == {
        "title",
        "description",
        "doc_type",
        "labels",
        "owner",
        "audiences",
        "language",
    }
    long = "Una frase. Dos frases. Tres frases. Cuatro frases que ya son demasiadas aquí."
    assert await errors(db, node, GOOD | {"description": long}) == [
        {"field": "description", "message": "1 to 3 sentences"}
    ]
    assert [
        e["field"] for e in await errors(db, node, GOOD | {"labels": [str(n) for n in range(16)]})
    ] == ["labels"]


async def test_archived_catalog_entries_are_refused(db: AsyncSession, node, team: Team) -> None:  # type: ignore[no-untyped-def]
    admin = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert admin is not None
    await catalogs.update(db, admin, "doc-types", "how-to", catalogs.EntryChanges(archived=True))
    assert [e["field"] for e in await errors(db, node, GOOD)] == ["doc_type"]
