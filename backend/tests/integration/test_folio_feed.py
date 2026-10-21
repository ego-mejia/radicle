"""Para ti (Folio 2.4, 2.7): what you follow, then the week's most read."""

from datetime import UTC

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import views
from radicle.platform.db.models import utcnow
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


async def test_following_first_then_popular(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i, m = team.instance.headers, team.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    made = {}
    for title in ("Seguida", "Popular", "Callada"):
        r = await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
        )
        made[title] = r.json()["id"]
        await publish(client, team, made[title])
    assert (await client.put(f"{API}/watch/node/{made['Seguida']}", headers=m)).status_code == 204
    for who in (team.viewer.headers, team.admin.headers):
        await client.get(f"{API}/nodes/{made['Popular']}", headers=who)
    await views.count_day(db, utcnow().astimezone(UTC).date())

    items = (await client.get(f"{API}/me/feed", headers=m)).json()["items"]
    assert [(f["title"], f["reason"]) for f in items] == [
        ("Seguida", "following"),
        ("Popular", "popular"),
    ]
    r = await client.get(f"{API}/me/feed", params={"limit": 1}, headers=m)
    assert [f["title"] for f in r.json()["items"]] == ["Seguida"]
    assert (await client.get(f"{API}/me/feed", params={"limit": 0}, headers=m)).status_code == 422
