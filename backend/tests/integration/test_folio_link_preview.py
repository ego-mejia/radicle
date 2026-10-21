"""Link previews over REST, without reaching inside the network (Folio 3.7)."""

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import link_preview
from radicle.platform.services import safe_fetch
from tests.conftest import Clock, Team
from tests.integration.folio_helpers import API

PAGE = """<html><head><meta property="og:title" content="El post">
<meta property="og:description" content="Lo que hay que saber."></head></html>"""


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A fake internet: every host resolves to its own entry, and the fetches are recorded."""
    dns = {
        "blog.example.com": ["93.184.216.34"],
        "www.youtube.com": ["142.250.80.46"],
        "evil.example.com": ["10.0.0.5"],
        "redirects.example.com": ["93.184.216.35"],
    }
    seen: list[str] = []

    async def resolve(host: str) -> list[str]:
        if host not in dns:
            raise OSError("no such host")
        return dns[host]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.headers['host']}{request.url.path} via {request.url.host}")
        if request.headers["host"] == "redirects.example.com":
            return httpx.Response(302, headers={"location": "http://evil.example.com/admin"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGE)

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(handler))
    return seen


async def test_a_card_from_the_page_and_the_cache(
    client: AsyncClient, db: AsyncSession, team: Team, web: list[str], clock: Clock
) -> None:
    h = team.member.headers
    url = "https://blog.example.com/post"
    r = await client.get(f"{API}/link-preview", params={"url": url}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "El post" and r.json()["embed_url"] is None
    assert web == ["blog.example.com/post via 93.184.216.34"]  # pinned to the checked address
    await client.get(f"{API}/link-preview", params={"url": url}, headers=h)
    assert len(web) == 1  # cached
    clock.advance(hours=25)  # the service directly: a session wouldn't last that long
    assert (await link_preview.preview(db, url)).title == "El post"
    assert len(web) == 2  # fetched again after 24 hours


async def test_embeddable_providers(client: AsyncClient, team: Team, web: list[str]) -> None:
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    r = await client.get(f"{API}/link-preview", params={"url": url}, headers=team.member.headers)
    body = r.json()
    assert body["provider"] == "youtube"
    assert body["embed_url"] == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"


@pytest.mark.parametrize(
    ("url", "says"),
    [
        ("http://127.0.0.1:8000/api/v1/me", "not a public address"),
        ("http://169.254.169.254/latest/meta-data/", "not a public address"),
        ("http://evil.example.com/", "not a public address"),
        ("https://redirects.example.com/x", "not a public address"),
        ("ftp://blog.example.com/file", "Only http and https"),
        ("https://nowhere.example.com/", "could not be found"),
    ],
)
async def test_never_inside_the_network(
    client: AsyncClient, team: Team, web: list[str], url: str, says: str
) -> None:
    r = await client.get(f"{API}/link-preview", params={"url": url}, headers=team.member.headers)
    assert r.status_code == 422 and says in r.json()["detail"], r.text
    assert not any("evil" in s or "127.0.0.1" in s for s in web)
