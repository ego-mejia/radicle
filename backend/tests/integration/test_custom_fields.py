import pytest
from httpx import AsyncClient

from tests.conftest import Team, new_ticket, patch_ticket


@pytest.fixture
async def board(client: AsyncClient, board: Team) -> Team:
    """PA detached from Radicle default, so its fields can be edited here."""
    r = await client.post("/api/v1/projects/PA/detach", headers=board.instance.headers)
    assert r.status_code == 200, r.text
    return board


API = "/api/v1"
FIELDS = f"{API}/projects/PA/fields"

ENVIRONMENT = {
    "key": "environment",
    "name": "Environment",
    "field_type": "select",
    "options": [{"value": "prod", "label": "Prod"}, {"value": "staging"}, {"value": "dev"}],
    "applies_to_types": ["bug"],
}


async def add_field(client: AsyncClient, team: Team, **body: object) -> dict:
    r = await client.post(FIELDS, headers=team.admin.headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def keys(client: AsyncClient, team: Team, q: str) -> list[str]:
    r = await client.get(f"{API}/tickets", headers=team.member.headers, params={"q": q})
    assert r.status_code == 200, r.text
    return sorted(t["key"] for t in r.json()["items"])


async def test_acceptance_environment_select_on_bugs(client: AsyncClient, board: Team) -> None:
    field = await add_field(client, board, **ENVIRONMENT)
    assert field["options"][1] == {"value": "staging", "label": "staging", "color": None}
    assert field["applies_to_types"] == ["bug"] and field["applies_to_areas"] is None

    bug = await new_ticket(client, board.member, type="bug", custom_fields={"environment": "prod"})
    assert bug["custom_fields"] == {"environment": "prod"}
    await new_ticket(client, board.member, type="bug", custom_fields={"environment": "dev"})
    await new_ticket(client, board.member, type="bug")

    assert await keys(client, board, "cf.environment = prod") == ["PA-1"]
    assert await keys(client, board, "cf.environment IN (prod, dev)") == ["PA-1", "PA-2"]
    assert await keys(client, board, "cf.environment != prod") == ["PA-2", "PA-3"]
    assert await keys(client, board, "cf.environment IS EMPTY") == ["PA-3"]

    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={
            "type": "bug",
            "title": "x",
            "area": "Backend",
            "custom_fields": {"environment": "qa"},
        },
    )
    assert r.status_code == 422
    assert (
        r.json()["detail"] == "'qa' is not an option of Environment. Options: prod, staging, dev."
    )
    assert r.json()["errors"] == [{"field": "cf.environment", "message": "invalid"}]


async def test_field_that_does_not_apply(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, **ENVIRONMENT)
    await add_field(
        client,
        board,
        key="contract",
        name="Contract",
        field_type="url",
        applies_to_areas=["Legal"],
    )
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.member.headers,
        json={
            "type": "task",
            "title": "x",
            "area": "Legal",
            "custom_fields": {"environment": "prod"},
        },
    )
    assert r.status_code == 422
    assert "does not apply" in r.json()["detail"] and "contract" in r.json()["detail"]

    t = await new_ticket(
        client, board.member, area="Legal", custom_fields={"contract": "https://x.mx/c"}
    )
    r = await patch_ticket(
        client, board.member, t["key"], area="Backend", custom_fields={"contract": "https://y.mx"}
    )
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "cf.contract"

    r = await patch_ticket(client, board.member, t["key"], custom_fields={"nope": 1})
    assert r.status_code == 422 and "Unknown custom field 'nope'" in r.json()["detail"]

    # Moving to another area hides the value but keeps it.
    r = await patch_ticket(client, board.member, t["key"], area="Backend")
    assert r.status_code == 200 and r.json()["custom_fields"] == {}
    r = await patch_ticket(client, board.member, t["key"], area="Legal")
    assert r.json()["custom_fields"] == {"contract": "https://x.mx/c"}


@pytest.mark.parametrize(
    ("field_type", "good", "stored", "bad"),
    [
        ("text", "  hola  ", "hola", 5),
        ("number", "2.50", 2.5, "dos"),
        ("number", 3, 3, float("inf")),
        ("date", "2026-11-30", "2026-11-30", "30/11/2026"),
        ("checkbox", True, True, "yes"),
        ("user", "@luis", "luis", "olga"),
        ("url", "https://radicle.dev", "https://radicle.dev", "ftp://radicle.dev"),
    ],
)
async def test_values_by_type(
    client: AsyncClient, board: Team, field_type: str, good: object, stored: object, bad: object
) -> None:
    await add_field(client, board, key="value", name="Value", field_type=field_type)
    t = await new_ticket(client, board.member)
    if field_type == "number" and bad == float("inf"):
        bad = "Infinity"
    r = await patch_ticket(client, board.member, t["key"], custom_fields={"value": bad})
    assert r.status_code == 422, r.text
    assert r.json()["errors"][0]["field"] == "cf.value"
    r = await patch_ticket(client, board.member, t["key"], custom_fields={"value": good})
    assert r.status_code == 200, r.text
    assert r.json()["custom_fields"] == {"value": stored}
    r = await patch_ticket(client, board.member, t["key"], custom_fields={"value": None})
    assert r.json()["custom_fields"] == {}


async def test_text_too_long(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, key="notes", name="Notes", field_type="text")
    t = await new_ticket(client, board.member)
    r = await patch_ticket(client, board.member, t["key"], custom_fields={"notes": "x" * 2001})
    assert r.status_code == 422 and "2000" in r.json()["detail"]


async def test_history_records_changes(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, **ENVIRONMENT)
    await add_field(client, board, key="owner", name="Owner", field_type="user")
    await new_ticket(client, board.member, type="bug", custom_fields={"environment": "dev"})
    r = await patch_ticket(
        client, board.member, "PA-1", custom_fields={"environment": "prod", "owner": "ana"}
    )
    assert r.json()["custom_fields"] == {"environment": "prod", "owner": "ana"}
    r = await patch_ticket(client, board.member, "PA-1", custom_fields={"environment": "prod"})
    assert r.json()["version"] == 2  # unchanged values do not bump the version
    events = (await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)).json()
    changed = [
        (e["field"], e["old_value"], e["new_value"])
        for e in events["items"]
        if e["event_type"] == "custom_field_changed"
    ]
    assert changed == [
        ("cf.owner", None, "ana"),
        ("cf.environment", "dev", "prod"),
        ("cf.environment", None, "dev"),
    ]


async def test_removed_option_keeps_value(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, **ENVIRONMENT)
    await new_ticket(client, board.member, type="bug", custom_fields={"environment": "staging"})
    r = await client.patch(
        f"{FIELDS}/environment",
        headers=board.admin.headers,
        json={"options": [{"value": "prod"}, {"value": "dev"}]},
    )
    assert r.status_code == 200, r.text
    ticket = (await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)).json()
    assert ticket["custom_fields"] == {"environment": "staging"}
    r = await patch_ticket(client, board.member, "PA-1", custom_fields={"environment": "staging"})
    assert r.status_code == 200  # an unchanged old value is not revalidated
    r = await patch_ticket(
        client, board.member, "PA-1", title="otro", custom_fields={"environment": "Dev"}
    )
    assert r.json()["custom_fields"] == {"environment": "dev"}


async def test_archive_hides_values_and_restore_shows_them(
    client: AsyncClient, board: Team
) -> None:
    await add_field(client, board, **ENVIRONMENT)
    await new_ticket(client, board.member, type="bug", custom_fields={"environment": "prod"})
    r = await client.delete(f"{FIELDS}/environment", headers=board.admin.headers)
    assert r.status_code == 204
    r = await client.get(FIELDS, headers=board.viewer.headers)
    assert r.json()["items"] == []
    r = await client.get(FIELDS, headers=board.viewer.headers, params={"include_archived": True})
    assert r.json()["items"][0]["archived"] is True
    ticket = (await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)).json()
    assert ticket["custom_fields"] == {}
    r = await client.get(
        f"{API}/tickets", headers=board.member.headers, params={"q": "cf.environment = prod"}
    )
    assert r.status_code == 422

    r = await client.patch(
        f"{FIELDS}/environment", headers=board.admin.headers, json={"archived": False}
    )
    assert r.json()["archived"] is False
    ticket = (await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)).json()
    assert ticket["custom_fields"] == {"environment": "prod"}


async def test_definition_validation(client: AsyncClient, board: Team) -> None:
    cases = [
        ({"key": "Bad Key", "name": "x", "field_type": "text"}, "key"),
        ({"key": "env", "name": "x", "field_type": "select"}, "options"),
        ({"key": "env", "name": "x", "field_type": "text", "options": [{"value": "a"}]}, "options"),
        (
            {
                "key": "env",
                "name": "x",
                "field_type": "select",
                "options": [{"value": "a"}, {"value": "A"}],
            },
            "options",
        ),
        (
            {
                "key": "env",
                "name": "x",
                "field_type": "select",
                "options": [{"value": "a", "color": "red"}],
            },
            "options",
        ),
        (
            {"key": "env", "name": "x", "field_type": "text", "applies_to_types": []},
            "applies_to_types",
        ),
        (
            {"key": "env", "name": "x", "field_type": "text", "applies_to_areas": ["Ventas"]},
            "applies_to_areas",
        ),
        ({"key": "env", "name": " ", "field_type": "text"}, "name"),
    ]
    for body, field in cases:
        r = await client.post(FIELDS, headers=board.admin.headers, json=body)
        assert r.status_code == 422, body
        assert r.json()["errors"][0]["field"] == field, r.json()

    await add_field(client, board, key="env", name="Env", field_type="text")
    r = await client.post(
        FIELDS,
        headers=board.admin.headers,
        json={"key": "cf.env", "name": "x", "field_type": "url"},
    )
    assert r.status_code == 409
    r = await client.patch(f"{FIELDS}/missing", headers=board.admin.headers, json={"name": "x"})
    assert r.status_code == 404 and "Fields: env" in r.json()["detail"]


async def test_area_restriction_can_be_changed(client: AsyncClient, board: Team) -> None:
    await add_field(
        client, board, key="contract", name="Contract", field_type="url", applies_to_areas=["Legal"]
    )
    r = await client.patch(
        f"{FIELDS}/contract",
        headers=board.admin.headers,
        json={
            "applies_to_areas": ["Legal", "Marketing"],
            "applies_to_types": ["task"],
            "position": 3,
        },
    )
    assert r.json()["applies_to_areas"] == ["Legal", "Marketing"]
    r = await client.patch(
        f"{FIELDS}/contract", headers=board.admin.headers, json={"applies_to_areas": None}
    )
    assert r.json()["applies_to_areas"] is None and r.json()["position"] == 3


@pytest.mark.parametrize(
    ("role", "status"),
    [("viewer", 403), ("member", 403), ("outsider", 404), ("admin", 201), ("agent", 403)],
)
async def test_permissions(client: AsyncClient, board: Team, role: str, status: int) -> None:
    actor = board.by_role(role)
    r = await client.post(
        FIELDS, headers=actor.headers, json={"key": "env", "name": "Env", "field_type": "text"}
    )
    assert r.status_code == status
    r = await client.get(FIELDS, headers=actor.headers)
    assert r.status_code == (404 if role == "outsider" else 200)


async def test_rql_operators(client: AsyncClient, board: Team) -> None:
    for body in (
        {"key": "notes", "name": "Notes", "field_type": "text"},
        {"key": "points", "name": "Points", "field_type": "number"},
        {"key": "signed", "name": "Signed", "field_type": "date"},
        {"key": "requires_signature", "name": "Requires signature", "field_type": "checkbox"},
        {"key": "owner", "name": "Owner", "field_type": "user"},
        {"key": "doc", "name": "Doc", "field_type": "url"},
    ):
        await add_field(client, board, **body)
    await new_ticket(
        client,
        board.member,
        custom_fields={
            "notes": "Revisar contrato",
            "points": 5,
            "signed": "2026-11-02",
            "requires_signature": True,
            "owner": "luis",
            "doc": "https://docs.example.com/contrato",
        },
    )
    await new_ticket(
        client,
        board.member,
        custom_fields={"notes": "otra cosa", "points": 1.5, "requires_signature": False},
    )
    await new_ticket(client, board.member)

    cases = {
        'cf.notes ~ "contrato"': ["PA-1"],
        'cf.notes = "OTRA COSA"': ["PA-2"],
        "cf.notes IS NOT EMPTY": ["PA-1", "PA-2"],
        "cf.points > 2": ["PA-1"],
        "cf.points <= 5": ["PA-1", "PA-2"],
        "cf.points = 1.5": ["PA-2"],
        "cf.points IS EMPTY": ["PA-3"],
        "cf.signed >= 2026-11-01": ["PA-1"],
        "cf.signed < 2026-11-01": [],
        "cf.signed = 2026-11-02": ["PA-1"],
        "cf.requires_signature = true": ["PA-1"],
        "cf.requires_signature = false": ["PA-2", "PA-3"],
        "cf.owner = luis": ["PA-1"],
        "cf.owner = currentUser()": ["PA-1"],
        "cf.owner IN (ana, luis)": ["PA-1"],
        "cf.owner != luis": ["PA-2", "PA-3"],
        "cf.doc ~ docs.example": ["PA-1"],
        "cf.doc !~ docs.example": ["PA-2", "PA-3"],
    }
    for q, expected in cases.items():
        assert await keys(client, board, q) == expected, q


async def test_rql_errors(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, **ENVIRONMENT)
    await add_field(client, board, key="points", name="Points", field_type="number")
    await add_field(client, board, key="ok", name="Ok", field_type="checkbox")
    await add_field(client, board, key="owner", name="Owner", field_type="user")
    cases = {
        "cf.enviroment = prod": "Did you mean 'cf.environment'?",
        "cf.environment > prod": "Use =, !=",
        "cf.points = mucho": "not a number",
        "cf.ok = maybe": "true or false",
        "cf.ok IS EMPTY": "cannot be EMPTY",
        "cf.points IN (1, 2)": "does not support IN",
        "cf.owner = now()": "currentUser()",
    }
    for q, message in cases.items():
        r = await client.get(f"{API}/tickets", headers=board.member.headers, params={"q": q})
        assert r.status_code == 422, q
        assert message in r.json()["detail"], (q, r.json()["detail"])


async def test_search_fields_lists_custom_fields(client: AsyncClient, board: Team) -> None:
    await add_field(client, board, **ENVIRONMENT)
    r = await client.get(
        f"{API}/search/fields", headers=board.viewer.headers, params={"project": "PA"}
    )
    custom = r.json()["values"]["custom_fields"]
    assert custom == [
        {
            "name": "cf.environment",
            "type": "select",
            "operators": ["=", "!="],
            "supports_in": True,
            "supports_empty": True,
            "description": "Environment",
            "values": ["prod", "staging", "dev"],
        }
    ]
