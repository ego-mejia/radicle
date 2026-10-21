"""Shared setup for the database tests (Folio 3.6)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.platform.db.models import User
from tests.conftest import Team
from tests.integration.folio_helpers import API

STATUS = {
    "key": "status",
    "name": "Status",
    "type": "select",
    "options": {
        "choices": [
            {"value": "Idea", "color": "grey"},
            {"value": "Trial", "color": "yellow"},
            {"value": "Adopted", "color": "green"},
        ]
    },
}
COLUMNS = [
    {"key": "name", "name": "Name", "type": "text"},
    STATUS,
    {"name": "Owner", "type": "person"},
    {"name": "Seats", "type": "number"},
    {"name": "Since", "type": "date"},
    {"name": "Link", "type": "url"},
    {"name": "Tags", "type": "multi_select", "options": {"choices": [{"value": "ai"}]}},
    {"name": "Paid", "type": "checkbox"},
]


async def user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def inventory(client: AsyncClient, db: AsyncSession, team: Team) -> FolioNode:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "ai-tools", "name": "AI Tools"})
    r = await client.post(
        f"{API}/nodes",
        headers=i,
        json={"space": "ai-tools", "kind": "database", "title": "Inventario"},
    )
    assert r.status_code == 201, r.text
    node = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert node is not None
    return node
