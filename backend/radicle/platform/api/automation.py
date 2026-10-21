"""Admin, Integrations, Rules (Folio 5.6, shared with Docket; ADR 0042)."""

import uuid
from typing import Any

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.platform.api.deps import Db, InstanceAdmin
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import AutomationRule, AutomationRun
from radicle.platform.services import audit, automation

router = APIRouter(tags=["automation"])


class AutomationActionOut(Output):
    name: str
    label: str


class AutomationExampleOut(Output):
    name: str
    description: str
    trigger: dict[str, Any]
    actions: list[dict[str, Any]]


class AutomationRuleIn(Input):
    name: str = Field(min_length=1, max_length=120)
    trigger: dict[str, Any] = Field(
        description='{"type": "event", "event": "page.outdated"} or {"type": "schedule", '
        '"every": "day", "select": "folio.pages", "params": {"rql": "…"}}'
    )
    filter: dict[str, str] = Field(default_factory=dict, description='e.g. {"space": "docs"}')
    actions: list[dict[str, Any]] = Field(description='e.g. [{"type": "folio.add_label", …}]')
    active: bool = True


class AutomationRuleOut(Output):
    id: uuid.UUID
    name: str
    trigger: dict[str, Any]
    filter: dict[str, str]
    actions: list[dict[str, Any]]
    active: bool
    created_at: UtcDatetime
    last_run_at: UtcDatetime | None


class AutomationRunOut(Output):
    id: int
    status: str
    target: str
    log: list[str]
    created_at: UtcDatetime


def _out(rule: AutomationRule) -> AutomationRuleOut:
    return AutomationRuleOut(
        id=rule.id,
        name=rule.name,
        trigger=rule.trigger,
        filter=rule.filter,
        actions=rule.actions,
        active=rule.active,
        created_at=rule.created_at,
        last_run_at=rule.last_run_at,
    )


def _run(r: AutomationRun) -> AutomationRunOut:
    return AutomationRunOut(
        id=r.id, status=r.status.value, target=r.target, log=r.log, created_at=r.created_at
    )


def _view(rule: AutomationRule) -> dict[str, Any]:
    return {"name": rule.name, "trigger": rule.trigger, "actions": rule.actions}


@router.get("/automation/actions", response_model=list[AutomationActionOut])
async def list_automation_actions(_: InstanceAdmin) -> list[AutomationActionOut]:
    return [AutomationActionOut(name=n, label=label) for n, label in automation.actions().items()]


@router.get("/automation/examples", response_model=list[AutomationExampleOut])
async def list_automation_examples(_: InstanceAdmin) -> list[AutomationExampleOut]:
    """Ready-made rules to start from; fill what's empty (e.g. the integration)."""
    return [AutomationExampleOut(**e) for e in automation.examples()]


@router.get("/automation/rules", response_model=list[AutomationRuleOut])
async def list_automation_rules(_: InstanceAdmin, db: Db) -> list[AutomationRuleOut]:
    return [_out(r) for r in await automation.list_all(db)]


@router.post("/automation/rules", response_model=AutomationRuleOut, status_code=201)
async def create_automation_rule(
    body: AutomationRuleIn, admin: InstanceAdmin, db: Db
) -> AutomationRuleOut:
    """The actions run with your permissions."""
    rule = await automation.create(
        db, admin, body.name, body.trigger, body.actions, body.filter, body.active
    )
    audit.record(
        db, admin, "automation.create", target_type="rule", target_id=rule.id, after=_view(rule)
    )
    return _out(rule)


@router.get("/automation/rules/{rule_id}", response_model=AutomationRuleOut)
async def get_automation_rule(rule_id: uuid.UUID, _: InstanceAdmin, db: Db) -> AutomationRuleOut:
    return _out(await automation.get(db, rule_id))


@router.put("/automation/rules/{rule_id}", response_model=AutomationRuleOut)
async def update_automation_rule(
    rule_id: uuid.UUID, body: AutomationRuleIn, admin: InstanceAdmin, db: Db
) -> AutomationRuleOut:
    rule = await automation.get(db, rule_id)
    before = _view(rule)
    await automation.update(
        db, rule, body.name, body.trigger, body.actions, body.filter, body.active
    )
    audit.record(
        db,
        admin,
        "automation.update",
        target_type="rule",
        target_id=rule.id,
        before=before,
        after=_view(rule),
    )
    return _out(rule)


@router.delete("/automation/rules/{rule_id}", status_code=204)
async def delete_automation_rule(rule_id: uuid.UUID, admin: InstanceAdmin, db: Db) -> Response:
    rule = await automation.get(db, rule_id)
    audit.record(
        db, admin, "automation.delete", target_type="rule", target_id=rule.id, before=_view(rule)
    )
    await db.delete(rule)
    return Response(status_code=204)


@router.get("/automation/rules/{rule_id}/runs", response_model=list[AutomationRunOut])
async def list_automation_runs(
    rule_id: uuid.UUID, _: InstanceAdmin, db: Db
) -> list[AutomationRunOut]:
    """The latest 50 runs, newest first, with what each action did."""
    return [_run(r) for r in await automation.runs(db, await automation.get(db, rule_id))]
