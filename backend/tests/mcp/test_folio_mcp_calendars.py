"""Calendar tools over MCP (Folio 5.8): an agent adds a release and reads it back with the
Docket milestones."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team
from tests.integration.folio_calendar_helpers import eng_space
from tests.integration.folio_helpers import API, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload


async def test_an_agent_adds_and_reads_events(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    await eng_space(client, db, board)
    body = {"space": "eng", "name": "Releases", "docket_projects": ["PA"]}
    r = await client.post(f"{API}/calendars", headers=board.instance.headers, json=body)
    assert r.status_code == 201, r.text
    async with folio_mcp(client, board.agent) as folio:
        event = {
            "space": "eng",
            "calendar": "releases",
            "title": "Release 2.0",
            "start_at": "2026-12-10T15:00:00Z",
            "end_at": "2026-12-10T16:00:00Z",
            "category": "release",
        }
        text = error_text(await folio.call_tool("add_calendar_event", event))
        assert "not found" in text.lower()  # the agent can't see eng yet
        await agent_can_write(client, board, "eng")
        made = payload(await folio.call_tool("add_calendar_event", event))
        assert made["calendar"] == "Releases" and made["category"] == "release"
        args = {"space": "eng", "start": "2026-12-01", "days": 31}
        listed = payload(await folio.call_tool("list_calendar_events", args))
        assert [c["calendar"] for c in listed] == ["Releases"]
        assert [e["title"] for e in listed[0]["events"]] == ["Release 2.0"]
        assert [m["name"] for m in listed[0]["milestones"]] == ["V1"]
        one = payload(
            await folio.call_tool(
                "list_calendar_events", args | {"calendar": made and listed[0]["id"]}
            )
        )
        assert len(one) == 1
        text = error_text(await folio.call_tool("add_calendar_event", event | {"calendar": "Nada"}))
        assert "Its calendars: Releases" in text
        text = error_text(await folio.call_tool("list_calendar_events", {"space": "nope"}))
        assert "not found" in text.lower()
