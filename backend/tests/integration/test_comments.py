from urllib.parse import quote

from httpx import AsyncClient

from tests.conftest import Team, new_ticket

API = "/api/v1"


async def comment(client: AsyncClient, actor, body: str, key: str = "PA-1"):  # type: ignore[no-untyped-def]
    return await client.post(
        f"{API}/tickets/{key}/comments", headers=actor.headers, json={"body_md": body}
    )


async def test_acceptance_comment_lifecycle(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await comment(client, board.member, "**Listo** el endpoint, @ana revisa?")
    assert r.status_code == 201
    c = r.json()
    assert c["author"]["handle"] == "luis" and c["ticket"] == "PA-1" and c["deleted"] is False

    r = await client.put(
        f"{API}/comments/{c['id']}/reactions/{quote('👍')}", headers=board.admin.headers
    )
    assert r.json()["reactions"] == [{"emoji": "👍", "count": 1, "users": ["ana"]}]
    await client.put(
        f"{API}/comments/{c['id']}/reactions/{quote('👍')}", headers=board.member.headers
    )
    r = await client.put(
        f"{API}/comments/{c['id']}/reactions/{quote('🎉')}", headers=board.member.headers
    )
    assert [(x["emoji"], x["count"]) for x in r.json()["reactions"]] == [("👍", 2), ("🎉", 1)]
    r = await client.delete(
        f"{API}/comments/{c['id']}/reactions/{quote('🎉')}", headers=board.member.headers
    )
    assert [x["emoji"] for x in r.json()["reactions"]] == ["👍"]

    r = await client.patch(
        f"{API}/comments/{c['id']}", headers=board.member.headers, json={"body_md": "Editado"}
    )
    assert r.json()["body_md"] == "Editado" and r.json()["edited_at"] is not None
    r = await client.delete(f"{API}/comments/{c['id']}", headers=board.member.headers)
    assert r.status_code == 204

    r = await client.get(f"{API}/tickets/PA-1/comments", headers=board.viewer.headers)
    [placeholder] = r.json()["items"]
    assert placeholder["deleted"] is True and placeholder["body_md"] == ""
    r = await client.get(f"{API}/tickets/PA-1", headers=board.viewer.headers)
    assert r.json()["comments_count"] == 0
    r = await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)
    kinds = [e["event_type"] for e in r.json()["items"][:3]]
    assert kinds == ["comment_deleted", "comment_edited", "comment_added"]


async def test_comment_permissions(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    c = (await comment(client, board.member, "mío")).json()
    assert (await comment(client, board.viewer, "x")).status_code == 403
    assert (await comment(client, board.outsider, "x")).status_code == 404
    r = await client.patch(
        f"{API}/comments/{c['id']}", headers=board.admin.headers, json={"body_md": "hack"}
    )
    assert r.status_code == 403 and "Only the author" in r.json()["detail"]
    r = await client.delete(f"{API}/comments/{c['id']}", headers=board.agent.headers)
    assert r.status_code == 403
    r = await client.put(
        f"{API}/comments/{c['id']}/reactions/{quote('👍')}", headers=board.viewer.headers
    )
    assert r.status_code == 403
    r = await client.patch(
        f"{API}/comments/{c['id']}", headers=board.outsider.headers, json={"body_md": "x"}
    )
    assert r.status_code == 404
    # Project admins can delete other people's comments.
    assert (
        await client.delete(f"{API}/comments/{c['id']}", headers=board.admin.headers)
    ).status_code == 204
    assert (
        await client.delete(f"{API}/comments/{c['id']}", headers=board.admin.headers)
    ).status_code == 404


async def test_comment_validation(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    assert (await comment(client, board.member, "   ")).status_code == 422
    assert (await comment(client, board.member, "x" * 50_001)).status_code == 422
    assert (await comment(client, board.member, "x" * 50_000)).status_code == 201
    c = (await comment(client, board.member, "ok")).json()
    for bad in ("a", "ab", "👍a", "1"):
        r = await client.put(
            f"{API}/comments/{c['id']}/reactions/{quote(bad)}", headers=board.member.headers
        )
        assert r.status_code == 422, bad
    for good in ("👍🏽", "👨‍👩‍👧", "❤️", "🇲🇽"):
        r = await client.put(
            f"{API}/comments/{c['id']}/reactions/{quote(good)}", headers=board.member.headers
        )
        assert r.status_code == 200, good
    r = await client.delete(
        f"{API}/comments/{c['id']}/reactions/{quote('🎉')}", headers=board.member.headers
    )
    assert r.status_code == 409


async def test_comment_order_and_pagination(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    for i in range(5):
        await comment(client, board.member, f"c{i}")
    r = await client.get(
        f"{API}/tickets/PA-1/comments", headers=board.member.headers, params={"limit": 3}
    )
    first = r.json()
    assert [c["body_md"] for c in first["items"]] == ["c0", "c1", "c2"]
    r = await client.get(
        f"{API}/tickets/PA-1/comments",
        headers=board.member.headers,
        params={"limit": 3, "cursor": first["next_cursor"]},
    )
    assert [c["body_md"] for c in r.json()["items"]] == ["c3", "c4"]
    r = await client.get(
        f"{API}/tickets/PA-1/comments",
        headers=board.member.headers,
        params={"order": "desc", "limit": 2},
    )
    assert [c["body_md"] for c in r.json()["items"]] == ["c4", "c3"]
    r = await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)
    assert r.json()["comments_count"] == 5


async def test_comment_mentions_stored(client: AsyncClient, board: Team, db) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from radicle.db.models import Mention, User

    await new_ticket(client, board.member)
    c = (await comment(client, board.member, "@ana mira `@luis`")).json()
    rows = list(
        await db.execute(
            select(User.handle, Mention.comment_id).join(
                Mention, Mention.mentioned_user_id == User.id
            )
        )
    )
    assert [(h, str(cid)) for h, cid in rows] == [("ana", c["id"])]
    await client.delete(f"{API}/comments/{c['id']}", headers=board.member.headers)
    assert list(await db.scalars(select(Mention.id))) == []
