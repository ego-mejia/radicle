"""Types and helpers shared by the MCP tools."""

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from radicle.mcp.api import api

TicketType = Literal["task", "bug", "draft"]
Priority = Literal["highest", "high", "medium", "low", "lowest"]
Resolution = Literal["done", "wont_do", "duplicate", "cannot_reproduce"]
LinkType = Literal["blocks", "relates_to", "duplicates", "clones"]
Key = Annotated[str, Field(description="Ticket key, e.g. PA-4")]


def compact(ticket: dict[str, Any]) -> dict[str, Any]:
    """Just enough to decide what to open next."""
    assignee = ticket.get("assignee")
    return {
        "key": ticket["key"],
        "title": ticket["title"],
        "type": ticket["type"],
        "status": ticket["status"]["name"],
        "category": ticket["status"]["category"],
        "priority": ticket["priority"],
        "assignee": assignee["handle"] if assignee else None,
        "area": ticket.get("area"),
        "milestone": ticket.get("milestone"),
        "tags": ticket.get("tags", []),
        "blocked": ticket.get("blocked", False),
        "due_date": ticket.get("due_date"),
    }


def detailed(ticket: dict[str, Any]) -> dict[str, Any]:
    """Full ticket without noise: people as handles, refs as keys."""
    out = dict(ticket)
    out["status"] = ticket["status"]["name"]
    out["category"] = ticket["status"]["category"]
    out["assignee"] = ticket["assignee"]["handle"] if ticket.get("assignee") else None
    out["reporter"] = ticket["reporter"]["handle"]
    out["collaborators"] = [c["handle"] for c in ticket.get("collaborators", [])]
    out["parent"] = ticket["parent"]["key"] if ticket.get("parent") else None
    out["links"] = [
        {
            "id": link["id"],
            "label": link["label"],
            "key": link["ticket"]["key"],
            "title": link["ticket"]["title"],
            "status": link["ticket"]["status"]["name"],
        }
        for link in ticket.get("links", [])
    ]
    out["attachments"] = [
        {"id": a["id"], "filename": a["filename"], "mime_type": a["mime_type"]}
        for a in ticket.get("attachments", [])
    ]
    for noisy in ("rank", "project", "deleted"):
        out.pop(noisy, None)
    if not out.get("warnings"):
        out.pop("warnings", None)
    return out


def comment_out(comment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": comment["id"],
        "author": comment["author"]["handle"],
        "body": comment["body_md"] if not comment["deleted"] else "(comment deleted)",
        "created_at": comment["created_at"],
        "edited": comment["edited_at"] is not None,
        "reactions": {r["emoji"]: r["count"] for r in comment.get("reactions", [])},
    }


async def _ticket(ctx: Context, key: str) -> dict[str, Any]:
    async with api(ctx) as client:
        result: dict[str, Any] = await client.call("GET", f"/tickets/{key}")
        return result


class APIErrorMessage(ToolError):
    """Plain tool error raised before any API call."""


def _search_out(page: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "total": page["total"],
        "items": [compact(t) for t in page["items"]],
        "next_cursor": page["next_cursor"],
    }
    if page.get("warnings"):
        out["warnings"] = [w["message"] for w in page["warnings"]]
    return out


def _rule_text(rule: dict[str, Any]) -> str:
    config = ", ".join(f"{k}={v}" for k, v in (rule.get("config") or {}).items())
    name = f"{rule['rule_type']}({config})" if config else rule["rule_type"]
    return f"{rule['kind']}: {name}"


def project_schema(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": p["key"],
        "name": p["name"],
        "your_role": p["role"],
        "archived": p["archived"],
        "template": (
            {
                "name": p["template"]["name"],
                "mode": p["template"]["mode"],
                "version": p["template"]["applied_version"],
            }
            if p.get("template")
            else None
        ),
        "blocked_policy": p.get("blocked_policy"),
        "areas": [a["name"] for a in p["areas"]],
        "milestones": [
            {"name": m["name"], "target_date": m["target_date"], "counts": m["counts"]}
            for m in p["milestones"]
            if m["status"] == "open"
        ],
        "workflows": {
            w["type"]: {
                "statuses": [f"{s['name']} ({s['category']})" for s in w["statuses"]],
                "transitions": [
                    {
                        "name": t["name"],
                        "from": t["from_status"] or "any not done",
                        "to": t["to_status"],
                        "resolutions": t["allowed_resolutions"],
                        "rules": [_rule_text(r) for r in t.get("rules", [])],
                    }
                    for t in w["transitions"]
                ],
            }
            for w in p["workflows"]
        },
        "members": [
            {"handle": m["handle"], "kind": m["kind"], "role": m["role"]} for m in p["members"]
        ],
        "custom_fields": [
            {
                "key": f["key"],
                "name": f["name"],
                "type": f["field_type"],
                "options": [o["value"] for o in f["options"]] or None,
                "applies_to_types": f["applies_to_types"],
                "applies_to_areas": f["applies_to_areas"],
            }
            for f in p.get("custom_fields", [])
        ],
    }
