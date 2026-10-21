"""RQL for docs (Folio 1.6): every field with its operators, the spec's examples, sorting,
paging, and errors that say where they are."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioActionItem
from radicle.folio.db.models import FolioGlobalGrant
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, METADATA


async def _page(
    client: AsyncClient, team: Team, title: str, parent: str | None = None, **meta: object
) -> str:
    i = team.instance.headers
    body = {"space": "docs", "kind": "page", "title": title, "parent": parent}
    nid = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
    md = f"# {title}\n\nTexto sobre {title.lower()}."
    r = await client.put(
        f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": md, "metadata": METADATA | meta}
    )
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})).status_code == 201
    return nid


@pytest.fixture
async def docs(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    await client.post(f"{API}/spaces", headers=i, json={"key": "ops", "name": "Ops"})
    guide = await _page(client, team, "Conecta un agente")
    deploy = await _page(client, team, "Despliegue", guide, doc_type="guide", labels=["ops"])
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "ops", "kind": "blog_post", "title": "Novedades"}
    )
    draft = r.json()["id"]
    await run_jobs(db)  # text ~ reads the search index
    return {"guide": guide, "deploy": deploy, "draft": draft}


async def ids(client: AsyncClient, team: Team, q: str, who: str = "member") -> list[str]:
    r = await client.get(f"{API}/nodes", params={"q": q}, headers=team.by_role(who).headers)
    assert r.status_code == 200, r.text
    return [d["id"] for d in r.json()["items"]]


async def test_every_field(client: AsyncClient, team: Team, docs: dict) -> None:
    g, d, draft = docs["guide"], docs["deploy"], docs["draft"]
    expected = {
        "space = docs": {g, d},
        "space IN (docs, ops)": {g, d, draft},
        "kind = blog_post": {draft},
        "doc_type IN (how-to, guia)": {g},
        "doc_type = guide": {d},
        "label = ops": {d},
        "#agentes": {g},
        "#ops AND audience = everyone AND language = es": {d},
        "owner = fernando": {g, d},
        "owner = currentUser()": {g, d},
        "owner = luis": set(),
        "doc_type IS EMPTY": {draft},
        "audience IS EMPTY": {draft},
        "kind = folder OR title ~ despl": {d},
        "space NOT IN (ops)": {g, d},
        "label != ops AND space = docs": {g},
        "title !~ agente AND space = docs": {d},
        "author IN (luis, fernando)": {g, d},
        "published = startOfDay() OR published > -1d": {g, d},
        "author = @fernando": {g, d},
        'title ~ "agente"': {g},
        "text ~ despliegue": {d},
        f"parent = {g[:6]}": {d},
        "parent IS EMPTY AND space = docs": {g},
        "published IS EMPTY": {draft},
        "published >= -30d": {g, d},
        "published < -30d": set(),
        "created >= startOfDay() AND updated <= now()": {g, d, draft},
        "label IS NOT EMPTY AND NOT kind = folder": {g, d},
    }
    for q, want in expected.items():
        assert set(await ids(client, team, q, "instance")) == want, q


async def test_phase_2_fields(
    client: AsyncClient, db: AsyncSession, team: Team, docs: dict
) -> None:
    g, d = docs["guide"], docs["deploy"]
    i, m = team.instance.headers, team.member.headers
    await client.patch(f"{API}/nodes/{g}/status", headers=i, json={"status": "verified"})
    assert (await client.put(f"{API}/watch/node/{d}", headers=m)).status_code == 204
    assert (await client.put(f"{API}/favorites/node/{g}", headers=m)).status_code == 204
    db.add(FolioActionItem(node_id=uuid.UUID(d), item_key="t1", text="Revisar", done=False))
    db.add(FolioActionItem(node_id=uuid.UUID(g), item_key="t2", text="Hecho", done=True))
    await db.flush()
    expected = {
        "status = verified": {g},
        "status IN (published, verified)": {g, d},
        "status != verified AND space = docs": {d},
        "watched_by = currentUser()": {d},
        f"watched_by = {team.member.handle}": {d},
        "favorite_of = currentUser()": {g},
        "has_open_tasks = true": {d},
        "has_open_tasks = false AND space = docs": {g},
    }
    for q, want in expected.items():
        assert set(await ids(client, team, q)) == want, q


async def test_spec_examples(client: AsyncClient, team: Team, docs: dict) -> None:
    q = "space = docs AND doc_type = how-to AND published >= -30d ORDER BY published DESC"
    assert await ids(client, team, q) == [docs["guide"]]
    assert await ids(client, team, "#agentes AND audience = everyone AND language = es") != []
    assert await ids(client, team, "kind = blog_post AND author = fernando") == []


async def test_sorting_and_paging(client: AsyncClient, team: Team, docs: dict) -> None:
    assert await ids(client, team, "space = docs ORDER BY title") == [docs["guide"], docs["deploy"]]
    i = team.instance.headers
    r = await client.get(f"{API}/nodes", params={"q": "ORDER BY title DESC", "limit": 2}, headers=i)
    first = r.json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    params = {"q": "ORDER BY title DESC", "limit": 2, "cursor": first["next_cursor"]}
    rest = (await client.get(f"{API}/nodes", params=params, headers=i)).json()
    assert [x["title"] for x in first["items"] + rest["items"]] == [
        "Novedades",
        "Despliegue",
        "Conecta un agente",
    ]
    assert rest["next_cursor"] is None and first["items"][0]["metadata"] is None


@pytest.mark.parametrize(
    ("q", "position", "says"),
    [
        ("spaec = docs", 0, "Did you mean 'space'"),
        ("kind = post", 7, "Use page, folder, blog_post"),
        ("title = x", 6, "Use ~, !~"),
        ("space = docs AND", 16, "end of query"),
        ("published >= ayer", 13, "is not a date"),
        ("owner = today()", 8, "currentUser()"),
        ("parent = zz", 9, "not a node id"),
        ("ORDER BY slug", 9, "Sortable: title"),
        ("text IS EMPTY", 0, "cannot be EMPTY"),
    ],
)
async def test_errors_say_where(
    client: AsyncClient, team: Team, docs: dict, q: str, position: int, says: str
) -> None:
    r = await client.get(f"{API}/nodes", params={"q": q}, headers=team.member.headers)
    assert r.status_code == 422, r.text
    assert r.json()["position"] == position and says in r.json()["detail"], r.json()


async def test_permissions(client: AsyncClient, db: AsyncSession, team: Team, docs: dict) -> None:
    assert docs["draft"] not in await ids(client, team, "")  # unpublished: admins only
    r = await client.get(f"{API}/nodes", params={"cursor": "nope"}, headers=team.member.headers)
    assert r.status_code == 422
    await db.execute(delete(FolioGlobalGrant))
    r = await client.get(f"{API}/nodes", headers=team.member.headers)
    assert r.status_code == 404 and "no access to Folio" in r.json()["detail"]
