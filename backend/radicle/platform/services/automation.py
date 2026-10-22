"""Automation rules (Folio 5.6, shared with Docket; ADR 0042): when a public event happens,
or on a schedule, run actions with the permissions of the admin who made the rule.

Apps register actions (`folio.add_label`) and schedule selectors (`folio.pages`);
platform brings `notify_person` and `notify_channel`. What
a rule's actions cause carries the chain of rules behind it, so a rule never runs twice
in one chain and a chain stops after MAX_CHAIN rules.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import (
    AutomationRule,
    AutomationRun,
    DeliveryStatus,
    Integration,
    OutboxEvent,
    User,
    utcnow,
)
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import chat_notices, events, integrations, queue, safe_fetch

RUN_JOB = "platform_run_automation"
SCHEDULE_JOB = "platform_automation_schedule"
MAX_CHAIN = 3
EVERY = {"hour": timedelta(hours=1), "day": timedelta(days=1)}


@dataclass
class Context:
    """What an action works on: the rule, its acting user and the event's data."""

    rule: AutomationRule
    actor: User
    data: dict[str, Any]
    log: list[str] = field(default_factory=list)


Run = Callable[[AsyncSession, Context, dict[str, Any]], Awaitable[str]]
Check = Callable[[dict[str, Any]], None]
Select = Callable[[AsyncSession, User, dict[str, Any]], Awaitable[list[dict[str, Any]]]]


@dataclass(frozen=True)
class Action:
    name: str
    label: str
    run: Run
    check: Check | None = None


_actions: dict[str, Action] = {}
_selectors: dict[str, Select] = {}
_examples: dict[str, dict[str, Any]] = {}


def action(name: str, label: str, *, check: Check | None = None) -> Callable[[Run], Run]:
    """Register an action; `check(params)` raises ValidationFailed for bad settings."""

    def register(fn: Run) -> Run:
        _actions[name] = Action(name, label, fn, check)
        return fn

    return register


def selector(name: str) -> Callable[[Select], Select]:
    """Register what a scheduled rule runs on: `fn(db, actor, params)` returns each target's
    data, shaped like a public event's data (with a `target` id)."""

    def register(fn: Select) -> Select:
        _selectors[name] = fn
        return fn

    return register


def example(name: str, description: str, trigger: dict[str, Any], steps: list[Any]) -> None:
    """A ready-made rule admins start from (fields left empty are theirs to fill). Keyed by
    name, so registering an app twice (main and the worker both do) lists it once."""
    _examples[name] = {
        "name": name,
        "description": description,
        "trigger": trigger,
        "actions": steps,
    }


def examples() -> list[dict[str, Any]]:
    return list(_examples.values())


def actions() -> dict[str, str]:
    return {a.name: a.label for a in _actions.values()}


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


def check(trigger: dict[str, Any], steps: list[dict[str, Any]]) -> None:
    kind = trigger.get("type")
    if kind == "event":
        known = events.public_events()
        if trigger.get("event") not in known:
            raise _invalid("trigger.event", f"Pick one of these events: {', '.join(known)}.")
    elif kind == "schedule":
        if trigger.get("every") not in EVERY:
            raise _invalid("trigger.every", "A schedule runs every hour or every day.")
        if trigger.get("select") not in _selectors:
            valid = ", ".join(sorted(_selectors))
            raise _invalid("trigger.select", f"Pick what it runs on: {valid}.")
    else:
        raise _invalid("trigger.type", "A trigger is an event or a schedule.")
    if not steps:
        raise _invalid("actions", "Add at least one action.")
    for n, step in enumerate(steps):
        found = _actions.get(str(step.get("type")))
        if found is None:
            raise _invalid(f"actions[{n}].type", f"Pick one of: {', '.join(sorted(_actions))}.")
        if found.check is not None:
            found.check(step)


async def create(
    db: AsyncSession,
    admin: User,
    name: str,
    trigger: dict[str, Any],
    steps: list[dict[str, Any]],
    filter: dict[str, str] | None = None,
    active: bool = True,
) -> AutomationRule:
    if not name.strip():
        raise _invalid("name", "Give the rule a name that says what it does.")
    check(trigger, steps)
    rule = AutomationRule(
        name=name.strip(),
        trigger=trigger,
        actions=steps,
        filter=filter or {},
        active=active,
        created_by=admin.id,
    )
    db.add(rule)
    await db.flush()
    return rule


async def update(
    db: AsyncSession,
    rule: AutomationRule,
    name: str,
    trigger: dict[str, Any],
    steps: list[dict[str, Any]],
    filter: dict[str, str] | None = None,
    active: bool = True,
) -> AutomationRule:
    if not name.strip():
        raise _invalid("name", "Give the rule a name that says what it does.")
    check(trigger, steps)
    rule.name, rule.trigger, rule.actions = name.strip(), trigger, steps
    rule.filter, rule.active = filter or {}, active
    await db.flush()
    return rule


async def list_all(db: AsyncSession) -> list[AutomationRule]:
    return list(await db.scalars(select(AutomationRule).order_by(AutomationRule.name)))


async def runs(db: AsyncSession, rule: AutomationRule, limit: int = 50) -> list[AutomationRun]:
    return list(
        await db.scalars(
            select(AutomationRun)
            .where(AutomationRun.rule_id == rule.id)
            .order_by(AutomationRun.id.desc())
            .limit(limit)
        )
    )


async def get(db: AsyncSession, rule_id: uuid.UUID) -> AutomationRule:
    rule = await db.get(AutomationRule, rule_id)
    if rule is None:
        raise NotFound("Rule not found. List them with GET /api/v1/automation/rules.")
    return rule


async def _start(
    db: AsyncSession,
    rule: AutomationRule,
    data: dict[str, Any],
    *,
    event_id: int | None,
    target: str,
    chain: list[str],
) -> None:
    run_id = await db.scalar(
        insert(AutomationRun)
        .values(
            rule_id=rule.id,
            event_id=event_id,
            target=target,
            data=data,
            chain=chain,
            status=DeliveryStatus.pending,
        )
        .on_conflict_do_nothing()
        .returning(AutomationRun.id)
    )
    if run_id is not None:  # None: this rule already ran for this event
        await queue.enqueue(db, RUN_JOB, run_id=run_id)


@events.subscriber
async def _on_event(
    db: AsyncSession, event: OutboxEvent, published: list[events.PublicEvent]
) -> None:
    chain = [str(c) for c in event.payload.get(events.CHAIN_KEY, [])]
    if len(chain) >= MAX_CHAIN:
        return
    rules = await db.scalars(select(AutomationRule).where(AutomationRule.active.is_(True)))
    for rule in rules:
        if rule.trigger.get("type") != "event" or str(rule.id) in chain:
            continue
        for public in published:
            scope_ok = all(public.scope.get(k) == v for k, v in rule.filter.items())
            if public.name == rule.trigger.get("event") and scope_ok:
                data = public.data | {"event": public.name, "summary": public.summary}
                await _start(db, rule, data, event_id=event.id, target="", chain=chain)


@queue.handler(RUN_JOB)
async def run(db: AsyncSession, run_id: int, **_: Any) -> None:
    found = await db.get(AutomationRun, run_id, with_for_update=True)
    if found is None or found.status != DeliveryStatus.pending:
        return
    rule = await db.get(AutomationRule, found.rule_id)
    actor = await db.get(User, rule.created_by) if rule and rule.created_by else None
    if rule is None or actor is None or not actor.is_active:
        found.status, found.log = DeliveryStatus.skipped, ["The rule's author is gone."]
        return
    ctx = Context(rule, actor, found.data)
    token = events.automation_chain.set((*found.chain, str(rule.id)))
    failed = False
    try:
        for step in rule.actions:
            try:
                async with db.begin_nested():
                    ctx.log.append(await _actions[step["type"]].run(db, ctx, step))
            except (ValidationFailed, NotFound, safe_fetch.Blocked, KeyError) as exc:
                failed = True
                ctx.log.append(f"{step.get('type')}: {getattr(exc, 'detail', exc)}")
    finally:
        events.automation_chain.reset(token)
    found.status = DeliveryStatus.failed if failed else DeliveryStatus.sent
    found.log = ctx.log
    await db.flush()


@queue.handler(SCHEDULE_JOB)
async def schedule(db: AsyncSession, **_: Any) -> None:
    """Run the scheduled rules that are due, once per target."""
    now = utcnow()
    rules = await db.scalars(select(AutomationRule).where(AutomationRule.active.is_(True)))
    for rule in rules:
        trigger = rule.trigger
        if trigger.get("type") != "schedule":
            continue
        every = EVERY.get(str(trigger.get("every")), EVERY["day"])
        if rule.last_run_at is not None and now - rule.last_run_at < every:
            continue
        actor = await db.get(User, rule.created_by) if rule.created_by else None
        pick = _selectors.get(str(trigger.get("select")))
        if actor is None or pick is None:
            continue
        rule.last_run_at = now
        stamp = now.strftime("%Y-%m-%dT%H")
        for data in await pick(db, actor, dict(trigger.get("params", {}))):
            target = f"{data.get('target', '')}@{stamp}"
            await _start(db, rule, data, event_id=None, target=target, chain=[])
    await db.flush()


# --- platform's own actions -------------------------------------------------------------


def _check_channel(step: dict[str, Any]) -> None:
    if not step.get("integration") or not str(step.get("route", "")).isdigit():
        raise _invalid("actions", "notify_channel needs an integration id and its route number.")


@action("notify_channel", "Post on a Slack or Teams channel", check=_check_channel)
async def notify_channel(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    integration = await db.get(Integration, uuid.UUID(str(step["integration"])))
    if integration is None:
        raise NotFound("The integration was removed.")
    routes = integrations.routes(integration)
    route = int(step["route"])
    if route >= len(routes):
        raise NotFound(f"The integration has no route {route}.")
    text = str(step.get("message") or ctx.data.get("summary") or ctx.rule.name)
    link = (ctx.data.get("page") or {}).get("url")
    event = events.PublicEvent(str(ctx.data.get("event", "")), {}, {}, text, link)
    await chat_notices.send(
        integration, routes[route].channel, chat_notices.text_for(integration.kind, event)
    )
    return f"notify_channel: posted on {integration.name}"


def _check_person(step: dict[str, Any]) -> None:
    if not str(step.get("handle", "")).strip():
        raise _invalid("actions", "notify_person needs the person's handle.")


@action("notify_person", "Notify a person in Radicle", check=_check_person)
async def notify_person(db: AsyncSession, ctx: Context, step: dict[str, Any]) -> str:
    handle = str(step["handle"]).lstrip("@")
    person = await db.scalar(select(User).where(User.handle == handle, User.is_active.is_(True)))
    if person is None:
        raise NotFound(f"Nobody is called @{handle}.")
    text = str(step.get("message") or ctx.data.get("summary") or ctx.rule.name)
    link = (ctx.data.get("page") or {}).get("url")
    payload = {"to": str(person.id), "title": text, "link": link, "rule": ctx.rule.name}
    await events.emit(db, "platform", "automation_notice", actor=None, payload=payload)
    return f"notify_person: told @{handle}"


@events.resolver("platform", "automation_notice", label="Automation rules that notify you")
async def _notice(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    p = event.payload
    return [
        events.Notice(
            uuid.UUID(p["to"]), "automation", p["title"], p.get("rule", ""), p.get("link")
        )
    ]
