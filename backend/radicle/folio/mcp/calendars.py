"""Calendar tools (Folio 5.8): an agent reads a space's events and Docket milestones, and
adds events. Calendars are named by id or by name within their space."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from radicle.platform.mcp.api import api

Space = Annotated[str, Field(description="The space's key, as list_spaces shows it")]
CalendarName = Annotated[str, Field(description="The calendar's name or id")]


def _pick(calendars: list[dict[str, Any]], wanted: str) -> dict[str, Any]:
    for c in calendars:
        if wanted in (c["id"], c["name"]) or c["name"].lower() == wanted.strip().lower():
            return c
    names = ", ".join(c["name"] for c in calendars) or "none yet"
    raise ToolError(f"No calendar {wanted!r} in this space. Its calendars: {names}.")


def _day(value: date) -> datetime:
    return datetime.combine(value, time(), tzinfo=UTC)


def register(server: MCPServer) -> None:
    @server.tool()
    async def list_calendar_events(
        ctx: Context,
        space: Space,
        calendar: Annotated[
            CalendarName | None, Field(description="One calendar; default all of the space's")
        ] = None,
        start: Annotated[date | None, Field(description="First day; default today")] = None,
        days: Annotated[int, Field(ge=1, le=400, description="How many days")] = 30,
    ) -> list[dict[str, Any]]:
        """Each calendar of a space with its events (vacations, releases, on-call, ...) and
        the Docket milestones due in the days asked, oldest first. Times are UTC; all-day
        events end at the midnight after their last day."""
        first = _day(start or datetime.now(UTC).date())
        params = {"start": first.isoformat(), "end": (first + timedelta(days=days)).isoformat()}
        async with api(ctx) as client:
            listed = (await client.call("GET", "/folio/calendars", params={"space": space}))[
                "items"
            ]
            chosen = [_pick(listed, calendar)] if calendar else listed
            out = []
            for c in chosen:
                agenda = await client.call(
                    "GET", f"/folio/calendars/{c['id']}/events", params=params
                )
                out.append(
                    {
                        "calendar": c["name"],
                        "id": c["id"],
                        "events": [
                            {
                                k: e[k]
                                for k in (
                                    "id",
                                    "title",
                                    "start_at",
                                    "end_at",
                                    "all_day",
                                    "category",
                                    "people",
                                    "description",
                                )
                            }
                            for e in agenda["events"]
                        ],
                        "milestones": agenda["milestones"],
                    }
                )
        return out

    @server.tool()
    async def add_calendar_event(
        ctx: Context,
        space: Space,
        calendar: CalendarName,
        title: str,
        start_at: Annotated[
            datetime, Field(description="ISO 8601 with a time zone, e.g. 2026-11-03T10:00:00Z")
        ],
        end_at: Annotated[
            datetime, Field(description="ISO 8601; for all-day events, the last day counts")
        ],
        all_day: bool = False,
        category: Literal["vacation", "release", "event", "oncall", "other"] = "event",
        description: str = "",
        people: Annotated[list[str], Field(description="Handles of people it involves")] = [],  # noqa: B006
    ) -> dict[str, Any]:
        """Add an event to one of the space's calendars. It takes the create permission
        in the space."""
        body = {
            "title": title,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "all_day": all_day,
            "category": category,
            "description": description,
            "people": people,
        }
        async with api(ctx) as client:
            listed = (await client.call("GET", "/folio/calendars", params={"space": space}))[
                "items"
            ]
            target = _pick(listed, calendar)
            made = await client.call("POST", f"/folio/calendars/{target['id']}/events", json=body)
        return {"calendar": target["name"]} | {
            k: made[k] for k in ("id", "title", "start_at", "end_at", "all_day", "category")
        }
