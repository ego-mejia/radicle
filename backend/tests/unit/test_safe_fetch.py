"""Fetching pasted URLs without reaching inside the network (SSRF)."""

import httpx
import pytest

from radicle.platform.services import safe_fetch
from radicle.platform.services.safe_fetch import Blocked, _public, fetch

DNS = {
    "blog.example.com": ["93.184.216.34"],
    "evil.example.com": ["10.0.0.5"],
    "mixed.example.com": ["93.184.216.36", "127.0.0.1"],
    "hops.example.com": ["93.184.216.35"],
    "loop.example.com": ["93.184.216.37"],
}


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    async def resolve(host: str) -> list[str]:
        if host not in DNS:
            raise OSError("no such host")
        return DNS[host]

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.headers["host"]
        calls.append(f"{host}{request.url.path} via {request.url.host}")
        if host == "hops.example.com":
            return httpx.Response(302, headers={"location": "http://evil.example.com/admin"})
        if host == "loop.example.com":
            return httpx.Response(301, headers={"location": "/again"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="x" * 2_000_000)

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(handler))
    return calls


async def test_fetches_public_pages_pinned_and_capped(seen: list[str]) -> None:
    page = await fetch("https://blog.example.com/post")
    assert page.status == 200 and len(page.text) == safe_fetch.MAX_BYTES
    assert seen == ["blog.example.com/post via 93.184.216.34"]


@pytest.mark.parametrize(
    ("url", "says"),
    [
        ("http://127.0.0.1:8000/api/v1/me", "not a public address"),
        ("http://[::1]/", "not a public address"),
        ("http://169.254.169.254/latest/meta-data/", "not a public address"),
        ("http://evil.example.com/", "not a public address"),
        ("http://mixed.example.com/", "not a public address"),
        ("https://hops.example.com/x", "not a public address"),
        ("https://loop.example.com/x", "too many times"),
        ("ftp://blog.example.com/file", "Only http and https"),
        ("https://nowhere.example.com/", "could not be found"),
    ],
)
async def test_never_inside_the_network(seen: list[str], url: str, says: str) -> None:
    with pytest.raises(Blocked, match=says):
        await fetch(url)
    assert not any("evil" in s or "127.0.0.1" in s for s in seen)


@pytest.mark.parametrize(
    ("address", "public"),
    [
        ("93.184.216.34", True),
        ("2606:2800:220:1:248:1893:25c8:1946", True),
        ("127.0.0.1", False),
        ("10.0.0.5", False),
        ("172.16.3.4", False),
        ("192.168.1.1", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("fd00::1", False),
        ("::ffff:127.0.0.1", False),
        ("0.0.0.0", False),  # noqa: S104 - a test value, nothing binds to it
        ("224.0.0.1", False),
    ],
)
def test_only_public_addresses(address: str, public: bool) -> None:
    assert _public(address) is public
