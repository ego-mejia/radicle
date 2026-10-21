from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import AuditEntry, utcnow
from radicle.platform.db.models import AuditApp
from radicle.platform.services import audit
from tests.conftest import ADMIN_PASSWORD, Team, make_project, new_ticket, patch_ticket

API = "/api/v1"


async def logged(client: AsyncClient, team: Team, **params: object) -> list[dict]:
    r = await client.get(f"{API}/audit", headers=team.instance.headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def every_action(client: AsyncClient, team: Team) -> None:
    """Run each action of the catalog once, through the API."""
    i, a = team.instance.headers, team.admin.headers
    other = AsyncClient(transport=client._transport, base_url="http://test")
    await other.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "bad"})
    await other.post(
        f"{API}/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}
    )
    await client.post(
        f"{API}/users",
        headers=i,
        json={
            "handle": "nora",
            "display_name": "Nora",
            "email": "nora@example.com",
            "password": "temporary-pass",
        },
    )
    await client.patch(f"{API}/users/nora", headers=i, json={"display_name": "Nora R."})
    await client.patch(f"{API}/users/nora", headers=i, json={"is_instance_admin": True})
    await client.patch(f"{API}/users/nora", headers=i, json={"is_active": False})
    token = (await client.post(f"{API}/me/tokens", headers=i, json={"name": "t"})).json()
    await client.delete(f"{API}/me/tokens/{token['id']}", headers=i)
    await client.post(f"{API}/agents", headers=i, json={"handle": "bot", "display_name": "Bot"})
    await client.patch(f"{API}/users/bot", headers=i, json={"display_name": "Bot 2"})
    await make_project(client, team.instance, "PZ")
    await client.patch(f"{API}/projects/PA", headers=a, json={"name": "Proyecto A"})
    await client.post(f"{API}/projects/PZ/archive", headers=i)
    await client.post(f"{API}/projects/PZ/unarchive", headers=i)
    await client.put(f"{API}/projects/PA/members/olga", headers=a, json={"role": "viewer"})
    await client.put(f"{API}/projects/PA/members/olga", headers=a, json={"role": "member"})
    await client.delete(f"{API}/projects/PA/members/olga", headers=a)
    await client.post(f"{API}/groups", headers=i, json={"name": "legal"})
    await client.patch(f"{API}/groups/legal", headers=i, json={"description": "Abogados"})
    await client.put(f"{API}/groups/legal/members/luis", headers=i)
    await client.delete(f"{API}/groups/legal/members/luis", headers=i)
    await client.put(f"{API}/projects/PA/group-roles/legal", headers=a, json={"role": "member"})
    await client.delete(f"{API}/projects/PA/group-roles/legal", headers=a)
    await client.delete(f"{API}/groups/legal", headers=i)
    grant = await client.post(
        f"{API}/folio/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": "luis", "role": "creator"},
    )
    await client.delete(f"{API}/folio/admin/grants/{grant.json()['id']}", headers=i)
    await client.put(
        f"{API}/projects/PA/permissions", headers=a, json={"member": {"ticket.delete": True}}
    )
    level = (
        await client.post(f"{API}/projects/PA/security-levels", headers=a, json={"name": "Privado"})
    ).json()
    await client.patch(f"{API}/security-levels/{level['id']}", headers=a, json={"name": "Priv"})
    await new_ticket(client, team.member)
    await patch_ticket(client, team.admin, "PA-1", security_level="Priv")
    await patch_ticket(client, team.admin, "PA-1", security_level=None)
    await client.delete(f"{API}/security-levels/{level['id']}", headers=a)
    templates = (await client.get(f"{API}/templates", headers=i)).json()["items"]
    await client.patch(
        f"{API}/templates/{templates[0]['id']}", headers=i, json={"description_md": "Default"}
    )
    await client.post(f"{API}/projects/PA/detach", headers=i)
    project = (await client.get(f"{API}/projects/PA", headers=i)).json()
    wf = next(w for w in project["workflows"] if w["type"] == "task")
    workflow = {
        "statuses": [
            {k: s[k] for k in ("ref", "name", "category", "is_initial")} for s in wf["statuses"]
        ],
        "transitions": [
            {
                "ref": t["ref"],
                "name": t["name"],
                "from": t["from_ref"],
                "to": t["to_ref"],
                "allowed_resolutions": t["allowed_resolutions"],
                "rules": [],
            }
            for t in wf["transitions"]
        ],
    }
    r = await client.put(
        f"{API}/projects/PA/workflows/task", headers=i, json={"workflow": workflow}
    )
    assert r.status_code == 200, r.text
    await client.put(f"{API}/projects/PA/settings", headers=a, json={"blocked_policy": "enforce"})
    await client.put(f"{API}/projects/PA/inbox-settings", headers=a, json={"enabled": True})
    sso = (
        await client.post(
            f"{API}/admin/sso-providers",
            headers=i,
            json={
                "name": "Google",
                "issuer_url": "https://accounts.google.com",
                "client_id": "x",
                "client_secret": "y",
            },
        )
    ).json()
    await client.patch(f"{API}/admin/sso-providers/{sso['id']}", headers=i, json={"enabled": False})
    await client.patch(f"{API}/admin/settings", headers=i, json={"password_login_enabled": True})
    await client.post(
        f"{API}/tickets/bulk",
        headers=team.member.headers,
        json={"keys": ["PA-1"], "operations": [{"op": "add_tag", "tag": "x"}]},
    )
    await client.delete(f"{API}/tickets/PA-1", headers=a)
    await client.post(f"{API}/tickets/PA-1/restore", headers=a)
    await client.post(f"{API}/projects/PZ/areas", headers=i, json={"name": "Backend"})
    r = await client.post(f"{API}/tickets/PA-1/move", headers=i, json={"target_project": "PZ"})
    assert r.status_code == 200, r.text


async def test_every_action_of_the_catalog_is_logged(client: AsyncClient, board: Team) -> None:
    await every_action(client, board)
    entries = []
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        r = await client.get(f"{API}/audit", headers=board.instance.headers, params=params)
        entries += r.json()["items"]
        cursor = r.json()["next_cursor"]
        if not cursor:
            break
    assert set(audit.ACTIONS) - {e["action"] for e in entries} == set()
    by_action = {e["action"]: e for e in entries}
    change = by_action["project.update"]
    assert change["details"]["before"]["name"] == "ProyectoA"
    assert change["details"]["after"]["name"] == "Proyecto A"
    assert change["actor"] == "ana" and change["project"] == "PA"
    assert change["ip"] == "10.0.0.1"
    assert by_action["user.login_failed"]["actor"] is None
    sso = by_action["sso.create"]
    assert (
        "client_secret" not in str(sso["details"]) and sso["details"]["after"]["name"] == "Google"
    )


async def test_filters_csv_and_project_admins(client: AsyncClient, board: Team) -> None:
    await every_action(client, board)
    logins = await logged(client, board, action="user")
    assert logins and all(e["action"].startswith("user.") for e in logins)
    mine = await logged(client, board, actor="ana", project="PA")
    assert mine and all(e["project"] == "PA" for e in mine)
    r = await client.get(
        f"{API}/audit.csv", headers=board.instance.headers, params={"action": "group"}
    )
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,created_at,actor") and len(lines) > 3
    # A project admin sees only their projects' entries; others get 403.
    r = await client.get(f"{API}/audit", headers=board.admin.headers)
    assert r.status_code == 200 and r.json()["items"]
    assert {e["project"] for e in r.json()["items"]} == {"PA"}
    r = await client.get(f"{API}/audit", headers=board.member.headers)
    assert r.status_code == 403


async def test_the_log_cannot_be_changed(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    entry = await db.scalar(select(AuditEntry).limit(1))
    assert entry is not None
    for statement in (
        "UPDATE audit_log SET action = 'x'",
        "DELETE FROM audit_log",
        "TRUNCATE audit_log",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            async with db.begin_nested():
                await db.execute(text(statement))


async def test_retention_removes_only_expired(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    db.add(
        AuditEntry(
            actor_kind="system",
            action="user.login",
            target_type="user",
            details={},
            created_at=utcnow() - timedelta(days=800),
        )
    )
    db.add(
        AuditEntry(
            actor_kind="system",
            action="user.login",
            target_type="user",
            details={},
            created_at=utcnow() - timedelta(days=700),
        )
    )
    await db.flush()
    before = len((await db.scalars(select(AuditEntry))).all())
    assert await audit.purge(db) == 1
    assert len((await db.scalars(select(AuditEntry))).all()) == before - 1
    # Back to the normal role: deleting is refused again.
    with pytest.raises(DBAPIError, match="append-only"):
        async with db.begin_nested():
            await db.execute(text("DELETE FROM audit_log"))


async def test_each_entry_names_its_app(client: AsyncClient, board: Team) -> None:
    await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "docs"})
    await client.patch(f"{API}/projects/PA", headers=board.admin.headers, json={"name": "PA 2"})
    apps = {e["action"]: e["app"] for e in await logged(client, board)}
    assert apps["group.create"] == "platform"
    assert apps["user.login"] == "platform"
    assert apps["project.update"] == "docket"


async def test_record_takes_an_explicit_app(db: AsyncSession, board: Team) -> None:
    entry = audit.record(db, None, "settings.change", target_type="ai", app=AuditApp.folio)
    await db.flush()
    assert entry.app == AuditApp.folio
