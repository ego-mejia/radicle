"""Planning tools: areas, milestones, boards, milestone progress and reports."""

from datetime import date
from typing import Annotated, Any, Literal
from urllib.parse import quote

from mcp.server.mcpserver import Context, MCPServer
from pydantic import BaseModel, ConfigDict, Field

from radicle.docket.mcp.api import api
from radicle.docket.mcp.tools.common import APIErrorMessage, compact

Board = Annotated[str, Field(description="Board id, from list_boards")]
Project = Annotated[str, Field(description="Project key, e.g. PA")]
ICON = "Icon name in kebab case, like rocket or shield"


class AreaChanges(BaseModel):
    """Fields to change. Omit a field to keep it; send null to clear color or icon."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    color: str | None = Field(default=None, description="Hex like #4D7C0F")
    icon: str | None = Field(default=None, description=ICON)
    position: int | None = None
    archived: bool | None = Field(
        default=None, description="true archives it (tickets keep it), false restores it"
    )


class MilestoneChanges(BaseModel):
    """Fields to change. Omit a field to keep it; send null to clear the target date."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = Field(default=None, description="Markdown")
    target_date: date | None = None
    status: Literal["open", "closed"] | None = Field(
        default=None, description="closed closes it, open reopens it"
    )
    position: int | None = None


def _area(a: dict[str, Any]) -> dict[str, Any]:
    return {k: a[k] for k in ("name", "color", "icon", "position", "archived")}


def _milestone(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": m["name"],
        "description": m["description_md"],
        "target_date": m["target_date"],
        "status": m["status"],
        "position": m["position"],
        "counts": m["counts"],
    }


def _changes(changes: BaseModel) -> dict[str, Any]:
    body = changes.model_dump(mode="json", exclude_unset=True)
    if not body:
        raise APIErrorMessage("Send at least one field in `changes`.")
    return body


def register(server: MCPServer) -> None:
    @server.tool()
    async def create_area(
        ctx: Context,
        project: Project,
        name: str,
        color: Annotated[str | None, Field(description="Hex like #4D7C0F")] = None,
        icon: Annotated[str | None, Field(description=ICON)] = None,
    ) -> dict[str, Any]:
        """Create an area (project admins). Names are unique per project, ignoring case."""
        body = {"name": name, "color": color, "icon": icon}
        async with api(ctx) as client:
            area = await client.call("POST", f"/projects/{project}/areas", json=body)
        return _area(area)

    @server.tool()
    async def update_area(
        ctx: Context,
        project: Project,
        area: Annotated[str, Field(description="Current area name")],
        changes: AreaChanges,
    ) -> dict[str, Any]:
        """Rename, recolor, change the icon, reorder, or archive and restore an area
        (project admins). Only the fields you send change."""
        body = _changes(changes)
        async with api(ctx) as client:
            out = await client.call(
                "PATCH", f"/projects/{project}/areas/{quote(area, safe='')}", json=body
            )
        return _area(out)

    @server.tool()
    async def create_milestone(
        ctx: Context,
        project: Project,
        name: str,
        description: Annotated[str, Field(description="Markdown")] = "",
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """Create an open milestone (project admins). Names are unique per project."""
        body = {
            "name": name,
            "description_md": description,
            "target_date": target_date.isoformat() if target_date else None,
        }
        async with api(ctx) as client:
            milestone = await client.call("POST", f"/projects/{project}/milestones", json=body)
        return _milestone(milestone)

    @server.tool()
    async def update_milestone(
        ctx: Context,
        project: Project,
        milestone: Annotated[str, Field(description="Current milestone name")],
        changes: MilestoneChanges,
    ) -> dict[str, Any]:
        """Rename, describe, set or clear the target date, reorder, close or reopen a
        milestone (project admins). Only the fields you send change."""
        body = _changes(changes)
        if "description" in body:
            body["description_md"] = body.pop("description")
        async with api(ctx) as client:
            out = await client.call(
                "PATCH", f"/projects/{project}/milestones/{quote(milestone, safe='')}", json=body
            )
        return _milestone(out)

    @server.tool()
    async def list_boards(
        ctx: Context, project: Annotated[str, Field(description="Project key, e.g. PA")]
    ) -> list[dict[str, Any]]:
        """Boards of a project with their kind (kanban or scrum) and columns."""
        async with api(ctx) as client:
            page = await client.call("GET", f"/projects/{project}/boards")
        return [
            {
                "id": b["id"],
                "name": b["name"],
                "kind": b["kind"],
                "columns": [{"name": c["name"], "wip_limit": c["wip_limit"]} for c in b["columns"]],
                "quick_filters": [q["name"] for q in b["quick_filters"]],
            }
            for b in page["items"]
        ]

    @server.tool()
    async def get_board(
        ctx: Context,
        board: Board,
        quick_filters: Annotated[
            list[str] | None, Field(description="Quick filter names to apply (AND)")
        ] = None,
    ) -> dict[str, Any]:
        """Columns with their tickets (summarized) and the count against each WIP limit."""
        async with api(ctx) as client:
            config = await client.call("GET", f"/boards/{board}")
            wanted = {n.lower() for n in quick_filters or []}
            ids = [q["id"] for q in config["quick_filters"] if q["name"].lower() in wanted]
            data = await client.call(
                "GET", f"/boards/{board}/data", params={"quick_filters": ids or None}
            )
        return {
            "name": config["name"],
            "columns": [
                {
                    "name": c["name"],
                    "count": c["count"],
                    "wip_limit": c["wip_limit"],
                    "over_limit": c["over_limit"],
                    "tickets": [compact(t) for t in c["tickets"]],
                }
                for c in data["columns"]
            ],
        }

    @server.tool()
    async def get_milestone_progress(
        ctx: Context,
        project: Annotated[str, Field(description="Project key, e.g. PA")],
        milestone: Annotated[str, Field(description="Milestone name, e.g. V1")],
    ) -> dict[str, Any]:
        """% done by count and hours, hours left, pace and forecast date; state is on_track,
        at_risk (forecast after the target), no_forecast (with the reason) or done."""
        async with api(ctx) as client:
            report = await client.call(
                "GET",
                "/reports/milestone_progress",
                params={"project": project, "milestone": milestone},
            )
        return dict(report["summary"])

    @server.tool()
    async def get_report(
        ctx: Context,
        type: Annotated[
            Literal[
                "burndown",
                "burnup",
                "velocity",
                "cfd",
                "control_chart",
                "sprint",
                "created_resolved",
                "distribution",
                "milestone_progress",
                "time",
            ],
            Field(description="Which report"),
        ],
        project: Annotated[str | None, Field(description="Project key")] = None,
        board: Annotated[str | None, Field(description="Board id (velocity, cfd...)")] = None,
        sprint: Annotated[str | None, Field(description="Sprint id (burndown, sprint)")] = None,
        milestone: Annotated[str | None, Field(description="Milestone name, with project")] = None,
        q: Annotated[str | None, Field(description="Extra RQL")] = None,
        from_date: date | None = None,
        to_date: date | None = None,
        field: Annotated[
            str | None, Field(description="distribution: area, priority, assignee, type...")
        ] = None,
        interval: Literal["day", "week"] = "day",
        by: Literal["ticket", "milestone", "area", "assignee"] = "ticket",
    ) -> dict[str, Any]:
        """Report data in hours, summarized for you to interpret: the summary plus the rows
        (the last 60 for long series). Same numbers as the REST endpoint."""
        params = {
            "project": project,
            "board": board,
            "sprint": sprint,
            "milestone": milestone,
            "q": q,
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
            "field": field,
            "interval": interval,
            "by": by,
        }
        async with api(ctx) as client:
            report = await client.call(
                "GET", f"/reports/{type}", params={k: v for k, v in params.items() if v}
            )
        rows = report["rows"]
        return {
            "title": report["title"],
            "summary": report["summary"],
            "columns": report["columns"],
            "rows": rows[-60:],
            "rows_total": len(rows),
        }
