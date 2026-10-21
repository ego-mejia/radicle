"""Previews of pasted links (Folio 3.7): a card with title, description, site and image
from the page's OpenGraph tags, cached 24 hours. Only YouTube, Figma, Loom, Google Docs
and GitHub gists embed interactively, and the iframe URL is built by Radicle from the
link, never taken from the remote page.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.templates import FolioLinkPreview
from radicle.platform.db.models import utcnow
from radicle.platform.services import safe_fetch

CACHE = timedelta(hours=24)
MAX_TEXT = 300


@dataclass(frozen=True)
class Preview:
    url: str
    title: str
    description: str
    site_name: str
    icon_url: str | None
    image_url: str | None
    provider: str | None
    embed_url: str | None  # set only for the providers that embed


def _youtube(url: str) -> str | None:
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.").removeprefix("m.")
    video = None
    if host == "youtu.be":
        video = parts.path.strip("/").split("/")[0]
    elif host == "youtube.com":
        if parts.path == "/watch":
            video = parse_qs(parts.query).get("v", [None])[0]
        elif parts.path.startswith(("/embed/", "/shorts/", "/live/")):
            video = parts.path.split("/")[2]
    if video and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video):
        return f"https://www.youtube-nocookie.com/embed/{video}"
    return None


def _figma(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname in ("figma.com", "www.figma.com") and re.match(
        r"^/(file|design|proto|board|slides)/", parts.path
    ):
        return f"https://www.figma.com/embed?embed_host=radicle&url={quote(url, safe='')}"
    return None


def _loom(url: str) -> str | None:
    match = re.match(r"^https://(www\.)?loom\.com/(share|embed)/([0-9a-f]{20,40})", url)
    return f"https://www.loom.com/embed/{match.group(3)}" if match else None


def _google_docs(url: str) -> str | None:
    match = re.match(
        r"^https://docs\.google\.com/(document|spreadsheets|presentation)/d/([A-Za-z0-9_-]+)",
        url,
    )
    if not match:
        return None
    kind, doc = match.groups()
    return f"https://docs.google.com/{kind}/d/{doc}/preview"


def _github(url: str) -> str | None:
    match = re.match(r"^https://gist\.github\.com/([\w-]+)/([0-9a-f]{20,40})", url)
    return f"https://gist.github.com/{match.group(1)}/{match.group(2)}.pibb" if match else None


PROVIDERS = (
    ("youtube", _youtube),
    ("figma", _figma),
    ("loom", _loom),
    ("google_docs", _google_docs),
    ("github", _github),
)


def embed_for(url: str) -> tuple[str | None, str | None]:
    """(provider, iframe URL) when the link is one of the embeddable providers."""
    for name, build in PROVIDERS:
        embed = build(url)
        if embed:
            return name, embed
    return None, None


class _Meta(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.icon: str | None = None
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v or "" for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"]
        elif tag == "link" and "icon" in a.get("rel", "").lower() and a.get("href"):
            self.icon = self.icon or a["href"]
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


def _absolute(base: str, link: str | None) -> str | None:
    if not link:
        return None
    full = urljoin(base, link)
    return full if full.startswith(("http://", "https://")) else None


def parse(url: str, html: str) -> Preview:
    meta = _Meta()
    meta.feed(html)
    m = meta.meta
    provider, embed = embed_for(url)
    host = urlsplit(url).hostname or ""
    return Preview(
        url=url,
        title=_clip(m.get("og:title") or m.get("twitter:title") or meta.title or url),
        description=_clip(m.get("og:description") or m.get("description") or ""),
        site_name=_clip(m.get("og:site_name") or host.removeprefix("www.")),
        icon_url=_absolute(url, meta.icon) or _absolute(url, "/favicon.ico"),
        image_url=_absolute(url, m.get("og:image") or m.get("twitter:image")),
        provider=provider,
        embed_url=embed,
    )


def _key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _from_row(row: FolioLinkPreview) -> Preview:
    _, embed = embed_for(row.url)
    return Preview(
        url=row.url,
        title=row.title,
        description=row.description,
        site_name=row.site_name,
        icon_url=row.icon_url,
        image_url=row.image_url,
        provider=row.provider,
        embed_url=embed if row.embed_html_allowed else None,
    )


async def preview(db: AsyncSession, url: str) -> Preview:
    """The link's preview, from the cache when it's younger than 24 hours."""
    url = url.strip()
    row = await db.get(FolioLinkPreview, _key(url))
    if row is not None and utcnow() - row.fetched_at < CACHE:
        return _from_row(row)
    fetched = await safe_fetch.fetch(url)
    page = (
        fetched.text if "html" in fetched.content_type.lower() or not fetched.content_type else ""
    )
    result = parse(fetched.url if fetched.status < 400 else url, page)
    if row is None:
        row = FolioLinkPreview(url_hash=_key(url), url=url)
        db.add(row)
    row.title, row.description, row.site_name = result.title, result.description, result.site_name
    row.icon_url, row.image_url = result.icon_url, result.image_url
    row.provider, row.embed_html_allowed = result.provider, result.embed_url is not None
    row.fetched_at = utcnow()
    await db.flush()
    return result
