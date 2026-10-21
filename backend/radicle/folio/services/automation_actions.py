"""Folio's automation actions and schedule targets (Folio 5.6, ADR 0042). They run with the
permissions of the rule's author, on the page the event or the schedule names."""

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.docket_links import TicketLinkKind
from radicle.folio.db.models import FolioDraft, FolioNode, FolioNodeLabel, NodeStatus
from radicle.folio.services import archive, doc_query, quality, rag, ticket_links
from radicle.folio.services.public_events import page_data
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import automation
from radicle.platform.services.automation import Context

STATUSES = ("in_review", "verified", "published")


def _invalid(message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": "actions", "message": "invalid"}])


async def _node(db: AsyncSession, ctx: Context) -> FolioNode:
    page = ctx.data.get("page") or {}
    node = await db.get(FolioNode, uuid.UUID(str(page.get("id")))) if page.get("id") else None
    if node is None or node.deleted_at is not None:
        raise NotFound("The page is gone.")
    return node


def _check_status(step: dict[str, Any]) -> None:
    if step.get("status") not in STATUSES:
        raise _invalid(f"folio.change_status needs a status: {', '.join(STATUSES)}.")


async def change_status(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    node = await _node(db, ctx)
    await quality.set_status(db, ctx.actor, node, NodeStatus(step["status"]))
    return f"folio.change_status: “{node.title}” is {step['status']}"


def _check_label(step: dict[str, Any]) -> None:
    if not str(step.get("label", "")).strip():
        raise _invalid("folio.add_label needs the label.")


async def add_label(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    """The label shows in filters right away and stays in the draft for the next version."""
    node = await _node(db, ctx)
    label = str(step["label"]).strip().lstrip("#").lower()
    await db.execute(
        insert(FolioNodeLabel).values(node_id=node.id, label=label).on_conflict_do_nothing()
    )
    draft = await db.get(FolioDraft, node.id)
    if draft is not None:
        labels = list(draft.metadata_.get("labels") or [])
        if label not in labels:
            draft.metadata_ = {**draft.metadata_, "labels": [*labels, label]}
    await rag.schedule(db, [node.id])
    return f"folio.add_label: “{node.title}” has #{label}"


def _check_ticket(step: dict[str, Any]) -> None:
    if not str(step.get("project", "")).strip():
        raise _invalid("folio.create_ticket needs the Docket project key.")


async def create_ticket(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    node = await _node(db, ctx)
    page = ctx.data["page"]
    ticket = await docket.create_ticket(
        db,
        docket.NewTicket(
            project=str(step["project"]).upper(),
            title=str(step.get("title") or f"Review “{node.title}”"),
            description_md=f"{ctx.data.get('summary') or ctx.rule.name}\n\n{page['url']}",
            type=str(step.get("ticket_type") or "task"),
            area=step.get("area"),
            milestone=step.get("milestone"),
        ),
        ctx.actor,
    )
    await ticket_links.upsert(db, node, ticket.id, TicketLinkKind.manual, ctx.actor, None)
    return f"folio.create_ticket: {ticket.key}"


async def archive_page(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    node = await _node(db, ctx)
    await archive.archive(db, ctx.actor, node)
    return f"folio.archive: “{node.title}”"


async def pages(db: AsyncSession, actor: User, params: dict[str, Any]) -> list[dict[str, Any]]:
    """The pages an RQL query finds (as the rule's author sees them), up to 200."""
    found = await doc_query.query(db, actor, str(params.get("rql", "")), limit=200)
    out = []
    for doc in found.items:
        data, _ = await page_data(db, doc.node)
        out.append(data | {"target": str(doc.node.id), "summary": doc.node.title})
    return out


def register() -> None:
    automation.action("folio.change_status", "Change a page's status", check=_check_status)(
        change_status
    )
    automation.action("folio.add_label", "Add a label to a page", check=_check_label)(add_label)
    automation.action(
        "folio.create_ticket", "Create a Docket ticket linked to the page", check=_check_ticket
    )(create_ticket)
    automation.action("folio.archive", "Archive the page")(archive_page)
    automation.selector("folio.pages")(pages)
    automation.example(
        "Outdated pages to a channel",
        "When a verified page expires, post it on a Slack or Teams channel.",
        {"type": "event", "event": "page.outdated"},
        [{"type": "notify_channel", "integration": "", "route": 0}],
    )
    automation.example(
        "Review what agents publish",
        "When a page is published in a space, label it and send it back to review.",
        {"type": "event", "event": "page.published"},
        [
            {"type": "folio.add_label", "label": "revisar"},
            {"type": "folio.change_status", "status": "in_review"},
        ],
    )
    automation.example(
        "Archive outdated pages",
        "Every day, archive the pages an RQL query finds (here, the outdated ones).",
        {
            "type": "schedule",
            "every": "day",
            "select": "folio.pages",
            "params": {"rql": "status = outdated"},
        },
        [{"type": "folio.archive"}],
    )


register()  # the worker imports this module to run rules
