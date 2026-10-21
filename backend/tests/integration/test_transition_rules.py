import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Ticket
from tests.conftest import Team, new_ticket, patch_ticket, run_jobs

API = "/api/v1"


def task_workflow(project: dict) -> dict:
    """The task workflow of a project detail as a PUT body (matched by ref)."""
    wf = next(w for w in project["workflows"] if w["type"] == "task")
    return {
        "statuses": [
            {
                "ref": s["ref"],
                "name": s["name"],
                "category": s["category"],
                "is_initial": s["is_initial"],
            }
            for s in wf["statuses"]
        ],
        "transitions": [
            {
                "ref": t["ref"],
                "name": t["name"],
                "from": t["from_ref"],
                "to": t["to_ref"],
                "allowed_resolutions": t["allowed_resolutions"],
                "rules": t["rules"],
            }
            for t in wf["transitions"]
        ],
    }


async def set_rules(client: AsyncClient, team: Team, transition: str, rules: list[dict]) -> None:
    project = (await client.get(f"{API}/projects/PA", headers=team.instance.headers)).json()
    workflow = task_workflow(project)
    for t in workflow["transitions"]:
        if t["ref"] == transition:
            t["rules"] = rules
    r = await client.put(
        f"{API}/projects/PA/workflows/task",
        headers=team.instance.headers,
        json={"workflow": workflow},
    )
    assert r.status_code == 200, r.text


async def move(client: AsyncClient, actor, key: str, to: str, **extra: object):  # type: ignore[no-untyped-def]
    return await client.post(
        f"{API}/tickets/{key}/transitions", headers=actor.headers, json={"to_status": to, **extra}
    )


async def to_review(client: AsyncClient, actor, key: str) -> None:  # type: ignore[no-untyped-def]
    for status in ("In Progress", "In Review"):
        r = await move(client, actor, key, status)
        assert r.status_code == 200, r.text


@pytest.fixture
async def rules_board(client: AsyncClient, board: Team) -> Team:
    r = await client.post(f"{API}/projects/PA/detach", headers=board.instance.headers)
    assert r.status_code == 200
    return board


def rule(rule_kind: str, rule_type: str, /, **config: object) -> dict:
    return {"kind": rule_kind, "rule_type": rule_type, "config": config}


async def test_acceptance_checklist_complete_blocks_complete(
    client: AsyncClient, rules_board: Team
) -> None:
    team = rules_board
    await set_rules(client, team, "complete", [rule("validator", "checklist_complete")])
    t = await new_ticket(
        client, team.member, description_md="- [x] Diseño\n- [ ] Pruebas\n- [ ] Deploy @luis"
    )
    await to_review(client, team.member, t["key"])
    r = await move(client, team.member, t["key"], "Done", resolution="done")
    assert r.status_code == 409
    body = r.json()
    assert body["type"].endswith("transition_rules_failed")
    assert body["detail"] == (
        "Cannot move PA-1 to 'Done': 2 checklist items are still open: 'Pruebas'; 'Deploy'."
    )
    assert body["failed_rules"] == [
        {
            "rule": "checklist_complete",
            "message": "2 checklist items are still open: 'Pruebas'; 'Deploy'.",
        }
    ]
    for index in (1, 2):
        r = await client.patch(
            f"{API}/tickets/PA-1/checklist/{index}",
            headers=team.member.headers,
            json={"checked": True},
        )
    r = await move(client, team.member, t["key"], "Done", resolution="done")
    assert r.status_code == 200 and r.json()["status"]["name"] == "Done"


async def test_conditions_hide_transitions_with_reasons(
    client: AsyncClient, rules_board: Team
) -> None:
    team = rules_board
    await set_rules(client, team, "start", [rule("condition", "only_assignee")])
    await set_rules(client, team, "close", [rule("condition", "only_roles", roles=["admin"])])
    await new_ticket(client, team.member, assignee="agent-backend")

    r = await client.get(f"{API}/tickets/PA-1/transitions", headers=team.member.headers)
    assert [o["name"] for o in r.json()] == []
    r = await client.get(
        f"{API}/tickets/PA-1/transitions",
        headers=team.member.headers,
        params={"include_unavailable": True},
    )
    reasons = {o["name"]: (o["available"], o["reasons"]) for o in r.json()}
    assert reasons["Start"] == (
        False,
        [{"rule": "only_assignee", "message": "Only the assignee can do this."}],
    )
    assert reasons["Close"][1][0]["message"] == "Only these roles can do this: admin."

    r = await move(client, team.member, "PA-1", "In Progress")
    assert r.status_code == 409
    assert r.json()["type"].endswith("transition_unavailable")
    assert (
        r.json()["detail"]
        == "You cannot move PA-1 to 'In Progress': Only the assignee can do this."
    )

    r = await client.get(f"{API}/tickets/PA-1/transitions", headers=team.agent.headers)
    assert [o["name"] for o in r.json()] == ["Start"]
    r = await move(client, team.agent, "PA-1", "In Progress")
    assert r.status_code == 200
    r = await move(client, team.admin, "PA-1", "Done", resolution="wont_do")
    assert r.status_code == 200


async def test_reporter_and_user_kind_conditions(client: AsyncClient, rules_board: Team) -> None:
    team = rules_board
    await set_rules(client, team, "start", [rule("condition", "only_reporter")])
    await set_rules(
        client, team, "send_to_review", [rule("condition", "only_user_kind", kind="human")]
    )
    await new_ticket(client, team.agent)  # reported by the agent
    assert (await move(client, team.member, "PA-1", "In Progress")).status_code == 409
    assert (await move(client, team.agent, "PA-1", "In Progress")).status_code == 200
    r = await move(client, team.agent, "PA-1", "In Review")
    assert r.status_code == 409 and "Only people can do this." in r.json()["detail"]
    assert (await move(client, team.member, "PA-1", "In Review")).status_code == 200


async def test_validators(client: AsyncClient, db: AsyncSession, rules_board: Team) -> None:
    team = rules_board
    r = await client.post(
        f"{API}/projects/PA/fields",
        headers=team.instance.headers,
        json={"key": "pr", "name": "Pull request", "field_type": "url"},
    )
    assert r.status_code == 201
    await set_rules(
        client,
        team,
        "start",
        [
            rule("validator", "field_required", field="cf.pr"),
            rule("validator", "field_required", field="milestone"),
            rule("validator", "has_estimate"),
        ],
    )
    await set_rules(
        client,
        team,
        "complete",
        [rule("validator", "children_done"), rule("validator", "has_worklog")],
    )
    parent = await new_ticket(client, team.member)
    await new_ticket(client, team.member, parent=parent["key"], title="Hijo")
    r = await move(client, team.member, "PA-1", "In Progress")
    assert r.status_code == 409
    assert [f["rule"] for f in r.json()["failed_rules"]] == [
        "field_required",
        "field_required",
        "has_estimate",
    ]
    assert "cf.pr must have a value" in r.json()["detail"]
    r = await patch_ticket(
        client,
        team.member,
        "PA-1",
        milestone="V1",
        estimate_hours=3,
        custom_fields={"pr": "https://github.com/x/y/pull/1"},
    )
    assert r.status_code == 200
    await to_review(client, team.member, "PA-1")

    r = await move(client, team.member, "PA-1", "Done", resolution="done")
    assert [f["message"] for f in r.json()["failed_rules"]] == [
        "These subtickets are not done yet: PA-2.",
        "Log time on the ticket first (at least one worklog).",
    ]
    assert (
        await move(client, team.member, "PA-2", "Done", resolution="wont_do")
    ).status_code == 200
    await db.execute(update(Ticket).where(Ticket.number == 1).values(time_spent_minutes=30))
    await db.commit()
    r = await move(client, team.member, "PA-1", "Done", resolution="done")
    assert r.status_code == 200, r.text


async def test_comment_required_saves_the_comment(client: AsyncClient, rules_board: Team) -> None:
    team = rules_board
    await set_rules(client, team, "stop", [rule("validator", "comment_required")])
    await new_ticket(client, team.member)
    await move(client, team.member, "PA-1", "In Progress")
    options = (
        await client.get(f"{API}/tickets/PA-1/transitions", headers=team.member.headers)
    ).json()
    assert next(o for o in options if o["name"] == "Stop")["requires_comment"] is True
    r = await move(client, team.member, "PA-1", "To Do", comment="   ")
    assert r.status_code == 409 and "needs a comment" in r.json()["detail"]
    r = await move(client, team.member, "PA-1", "To Do", comment="Falta definir alcance")
    assert r.status_code == 200 and r.json()["comments_count"] == 1
    comments = (
        await client.get(f"{API}/tickets/PA-1/comments", headers=team.member.headers)
    ).json()
    assert comments["items"][0]["body_md"] == "Falta definir alcance"


async def test_post_functions_run_in_order_with_the_same_actor(
    client: AsyncClient, rules_board: Team
) -> None:
    team = rules_board
    r = await client.post(
        f"{API}/projects/PA/fields",
        headers=team.instance.headers,
        json={"key": "stage", "name": "Stage", "field_type": "text"},
    )
    await set_rules(
        client,
        team,
        "start",
        [
            rule("post_function", "assign_to_actor"),
            rule("post_function", "set_field", field="priority", value="high"),
            rule("post_function", "set_field", field="cf.stage", value="build"),
            rule("post_function", "set_field", field="due_date", value="2026-12-01"),
            rule("post_function", "add_tag", tag="doing"),
            rule("post_function", "remove_tag", tag="backlog"),
            rule("post_function", "clear_field", field="milestone"),
            rule("post_function", "add_comment", template="{actor} movió de {from} a {to} {x}"),
        ],
    )
    await set_rules(client, team, "stop", [rule("post_function", "unassign")])
    await new_ticket(client, team.member, tags=["backlog"], milestone="V1")
    r = await move(client, team.agent, "PA-1", "In Progress")
    assert r.status_code == 200, r.text
    ticket = r.json()
    assert ticket["assignee"]["handle"] == "agent-backend"
    assert ticket["priority"] == "high" and ticket["due_date"] == "2026-12-01"
    assert ticket["custom_fields"] == {"stage": "build"}
    assert ticket["tags"] == ["doing"] and ticket["milestone"] is None
    comments = (
        await client.get(f"{API}/tickets/PA-1/comments", headers=team.member.headers)
    ).json()
    assert comments["items"][0]["body_md"] == "@agent-backend movió de To Do a In Progress {x}"
    history = (await client.get(f"{API}/tickets/PA-1/history", headers=team.member.headers)).json()
    recent = [e for e in history["items"] if e["event_type"] != "created"]
    assert {e["actor"]["handle"] for e in recent} == {"agent-backend"}
    assert recent[-1]["event_type"] == "status_changed"  # the move comes first

    r = await move(client, team.member, "PA-1", "To Do")
    assert r.json()["assignee"] is None


async def test_failing_post_function_undoes_the_move(
    client: AsyncClient, rules_board: Team
) -> None:
    team = rules_board
    await set_rules(
        client, team, "start", [rule("post_function", "set_field", field="area", value="Ventas")]
    )
    await new_ticket(client, team.member)
    r = await move(client, team.member, "PA-1", "In Progress")
    assert r.status_code == 422 and "Area 'Ventas' does not exist" in r.json()["detail"]
    ticket = (await client.get(f"{API}/tickets/PA-1", headers=team.member.headers)).json()
    assert ticket["status"]["name"] == "To Do" and ticket["version"] == 1
    history = (await client.get(f"{API}/tickets/PA-1/history", headers=team.member.headers)).json()
    assert [e["event_type"] for e in history["items"]] == ["created"]


async def test_conditions_run_before_validators(client: AsyncClient, rules_board: Team) -> None:
    team = rules_board
    await set_rules(
        client,
        team,
        "start",
        [rule("condition", "only_assignee"), rule("validator", "has_estimate")],
    )
    await new_ticket(client, team.member)
    r = await move(client, team.member, "PA-1", "In Progress")
    assert r.json()["type"].endswith("transition_unavailable")
    await patch_ticket(client, team.member, "PA-1", assignee="luis")
    r = await move(client, team.member, "PA-1", "In Progress")
    assert r.json()["type"].endswith("transition_rules_failed")


async def blocked_ticket(client: AsyncClient, team: Team) -> None:
    await new_ticket(client, team.member, title="Bloqueador")
    await new_ticket(client, team.member, title="Bloqueado")
    r = await client.post(
        f"{API}/tickets/PA-1/links",
        headers=team.member.headers,
        json={"type": "blocks", "target": "PA-2"},
    )
    assert r.status_code == 201


async def test_blocked_policy_warn_and_enforce(client: AsyncClient, rules_board: Team) -> None:
    team = rules_board
    await blocked_ticket(client, team)
    r = await move(client, team.member, "PA-2", "In Progress")
    assert r.status_code == 200
    assert r.json()["warnings"][0]["code"] == "blocked"
    await move(client, team.member, "PA-2", "To Do")

    r = await client.put(
        f"{API}/projects/PA/settings",
        headers=team.admin.headers,
        json={"blocked_policy": "enforce"},
    )
    assert r.status_code == 200
    r = await move(client, team.member, "PA-2", "In Progress", force=True)
    assert r.status_code == 409 and r.json()["type"].endswith("ticket_blocked")
    assert r.json()["detail"] == (
        "PA-2 is blocked by PA-1, which are not done, and PA does not let blocked tickets "
        "move to 'In Progress'. Finish the blockers first."
    )
    r = await move(client, team.admin, "PA-2", "Done", resolution="wont_do")
    assert r.status_code == 409 and "force it as admin" in r.json()["detail"]
    r = await move(client, team.admin, "PA-2", "In Progress", force=True)
    assert r.status_code == 200 and r.json()["warnings"][0]["code"] == "forced"
    history = (await client.get(f"{API}/tickets/PA-2/history", headers=team.member.headers)).json()
    assert history["items"][0]["new_value"]["forced"] is True
    # Moving back to a todo status is always allowed.
    assert (await move(client, team.member, "PA-2", "To Do")).status_code == 200


async def test_not_blocked_condition(client: AsyncClient, rules_board: Team) -> None:
    team = rules_board
    await set_rules(client, team, "start", [rule("condition", "not_blocked")])
    await blocked_ticket(client, team)
    options = (
        await client.get(f"{API}/tickets/PA-2/transitions", headers=team.member.headers)
    ).json()
    assert "Start" in [o["name"] for o in options]  # warn policy: offered
    await client.put(
        f"{API}/projects/PA/settings",
        headers=team.admin.headers,
        json={"blocked_policy": "enforce"},
    )
    options = (
        await client.get(f"{API}/tickets/PA-2/transitions", headers=team.member.headers)
    ).json()
    assert "Start" not in [o["name"] for o in options]
    r = await move(client, team.admin, "PA-2", "In Progress", force=True)
    assert r.status_code == 200


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (rule("condition", "nope"), "Unknown rule 'nope'"),
        (rule("validator", "only_assignee"), "'only_assignee' is a condition, not a validator"),
        (rule("condition", "only_roles", roles=["boss"]), "only_roles needs a list of roles"),
        (rule("condition", "only_user_kind", kind="robot"), "human or agent"),
        (rule("validator", "field_required"), "needs: field"),
        (rule("validator", "field_required", field="title"), "'title' cannot be used in rules"),
        (rule("validator", "has_estimate", extra=1), "does not take: extra"),
        (rule("post_function", "add_tag", tag="No Tag"), "Invalid tag"),
        (rule("post_function", "add_comment", template=" "), "needs a template"),
    ],
)
async def test_rule_config_validation(
    client: AsyncClient, rules_board: Team, bad: dict, message: str
) -> None:
    project = (await client.get(f"{API}/projects/PA", headers=rules_board.instance.headers)).json()
    workflow = task_workflow(project)
    workflow["transitions"][0]["rules"] = [bad]
    r = await client.put(
        f"{API}/projects/PA/workflows/task",
        headers=rules_board.instance.headers,
        json={"workflow": workflow},
    )
    assert r.status_code == 422
    assert message in r.json()["detail"], r.json()["detail"]


async def test_rules_travel_with_templates(
    client: AsyncClient, db: AsyncSession, rules_board: Team
) -> None:
    team = rules_board
    await set_rules(client, team, "complete", [rule("validator", "checklist_complete")])
    r = await client.post(
        f"{API}/projects/PA/save-as-template",
        headers=team.admin.headers,
        json={"name": "Con reglas"},
    )
    template = r.json()
    complete = next(
        t for t in template["config"]["workflows"]["task"]["transitions"] if t["ref"] == "complete"
    )
    assert complete["rules"] == [
        {"kind": "validator", "rule_type": "checklist_complete", "config": {}}
    ]
    r = await client.post(
        f"{API}/projects",
        headers=team.instance.headers,
        json={"key": "PB", "name": "B", "template_id": template["id"]},
    )
    pb = r.json()
    rules = next(
        t["rules"]
        for w in pb["workflows"]
        if w["type"] == "task"
        for t in w["transitions"]
        if t["ref"] == "complete"
    )
    assert rules == [{"kind": "validator", "rule_type": "checklist_complete", "config": {}}]

    config = template["config"]
    for t in config["workflows"]["task"]["transitions"]:
        if t["ref"] == "complete":
            t["rules"] = [rule("validator", "has_estimate")]
    r = await client.patch(
        f"{API}/templates/{template['id']}", headers=team.instance.headers, json={"config": config}
    )
    assert r.status_code == 200
    await run_jobs(db)
    pb = (await client.get(f"{API}/projects/PB", headers=team.instance.headers)).json()
    rules = next(
        t["rules"]
        for w in pb["workflows"]
        if w["type"] == "task"
        for t in w["transitions"]
        if t["ref"] == "complete"
    )
    assert rules == [{"kind": "validator", "rule_type": "has_estimate", "config": {}}]
    assert await db.scalar(select(Ticket.id).limit(1)) is None
