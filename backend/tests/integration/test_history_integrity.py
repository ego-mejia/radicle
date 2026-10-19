import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, new_ticket


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ticket_events SET new_value = '\"hacked\"'",
        "DELETE FROM ticket_events",
        "TRUNCATE ticket_events",
    ],
)
async def test_history_cannot_be_modified_from_sql(
    client: AsyncClient, board: Team, db: AsyncSession, statement: str
) -> None:
    await new_ticket(client, board.member)
    with pytest.raises(DBAPIError, match="append-only"):
        async with db.begin_nested():
            await db.execute(text(statement))
    count = await db.scalar(text("SELECT count(*) FROM ticket_events"))
    assert count == 1
