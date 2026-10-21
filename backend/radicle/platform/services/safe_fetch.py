"""Fetching URLs that people paste, without letting them reach inside the network (SSRF).

Only http and https; the host is resolved once and every address must be public (no
loopback, private, link-local such as cloud metadata, multicast or reserved ranges); the
request goes to that checked address, so a DNS answer can't change between the check and
the connection; redirects are followed by hand, up to three, each one checked again;
5 seconds and 1 MB at most.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from radicle.platform.errors import ValidationFailed

TIMEOUT = 5.0
MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
USER_AGENT = "Radicle link preview (+https://github.com/ego-mejia/radicle)"

# Replaced in tests.
transport: httpx.AsyncBaseTransport | None = None


async def resolve(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({str(info[4][0]) for info in infos})


class Blocked(ValidationFailed):
    code = "url_not_allowed"

    def __init__(self, message: str) -> None:
        super().__init__(message, errors=[{"field": "url", "message": "not allowed"}])


def _public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


@dataclass(frozen=True)
class Fetched:
    url: str  # after redirects
    status: int
    content_type: str
    text: str


async def _checked_address(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Blocked("Only http and https links can be previewed.")
    host = parts.hostname
    try:
        literal = ipaddress.ip_address(host)
        addresses = [str(literal)]
    except ValueError:
        try:
            addresses = await resolve(host)
        except OSError:
            raise Blocked(f"{host} could not be found.") from None
    if not addresses or not all(_public(a) for a in addresses):
        raise Blocked(f"{host} is not a public address, so it can't be previewed.")
    return host, addresses[0]


async def fetch(url: str) -> Fetched:
    """GET a public page and return at most MAX_BYTES of its text."""
    async with httpx.AsyncClient(
        transport=transport, timeout=TIMEOUT, follow_redirects=False
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            host, address = await _checked_address(url)
            parts = urlsplit(url)
            netloc = f"[{address}]" if ":" in address else address
            if parts.port:
                netloc += f":{parts.port}"
            pinned = urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))
            request = client.build_request(
                "GET",
                pinned,
                headers={"Host": parts.netloc, "User-Agent": USER_AGENT, "Accept": "text/html"},
                extensions={"sni_hostname": host},
            )
            try:
                response = await client.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise Blocked(f"{host} did not answer ({type(exc).__name__}).") from None
            try:
                if response.is_redirect and "location" in response.headers:
                    url = urljoin(url, response.headers["location"])
                    continue
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) >= MAX_BYTES:
                        break
                return Fetched(
                    url=url,
                    status=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    text=body[:MAX_BYTES].decode(response.encoding or "utf-8", errors="replace"),
                )
            finally:
                await response.aclose()
    raise Blocked("The link redirects too many times.")
