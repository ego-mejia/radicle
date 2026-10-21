"""Folio assets (Folio 1.2): upload images, files and video to a page and read them back."""

import pytest
from httpx import AsyncClient

from radicle.folio.services import assets
from tests.conftest import Team
from tests.integration.folio_helpers import publish
from tests.integration.test_attachments import png

API = "/api/v1/folio"


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    return r.json()


async def _upload(client: AsyncClient, team: Team, page: dict, name: str, data: bytes, **form):
    return await client.post(
        f"{API}/nodes/{page['id']}/assets",
        headers=team.instance.headers,
        files={"file": (name, data)},
        data=form,
    )


async def test_images_shrink_and_show_inline(client: AsyncClient, team: Team, page: dict) -> None:
    r = await _upload(client, team, page, "diagram.png", png(3000, 1000), resize="small")
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["width"], body["height"], body["mime_type"]) == (800, 267, "image/png")
    await publish(client, team, page["id"])
    shown = await client.get(body["url"], headers=team.member.headers)
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/png"
    assert shown.headers["content-disposition"].startswith("inline")
    assert shown.headers["x-content-type-options"] == "nosniff"


async def test_other_files_download(client: AsyncClient, team: Team, page: dict) -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    r = await _upload(client, team, page, "../../evil.svg", svg)
    assert r.status_code == 201 and r.json()["filename"] == "evil.svg"
    got = await client.get(r.json()["url"], headers=team.instance.headers)
    assert got.headers["content-disposition"].startswith("attachment")
    pdf = await _upload(client, team, page, "spec.pdf", b"%PDF-1.4\n%fake\n")
    assert pdf.json()["mime_type"] == "application/pdf"
    shown = await client.get(pdf.json()["url"], headers=team.instance.headers)
    assert shown.headers["content-disposition"].startswith("inline")


async def test_actionable_errors(
    client: AsyncClient, team: Team, page: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (await _upload(client, team, page, "x.txt", b"")).status_code == 422
    r = await _upload(client, team, page, "x.png", png(10, 10), resize="huge")
    assert r.status_code == 422 and "original, large" in r.json()["detail"]
    r = await _upload(client, team, page, "x.png", b"\x89PNG\r\n\x1a\nbroken")
    assert r.status_code == 422 and "could not be read" in r.json()["detail"]
    monkeypatch.setattr(assets, "max_bytes", lambda: 10)
    r = await _upload(client, team, page, "big.bin", b"x" * 100)
    assert r.status_code == 413 and "limit is" in r.json()["detail"]
    r = await client.get(
        f"{API}/assets/00000000-0000-0000-0000-000000000000", headers=team.instance.headers
    )
    assert r.status_code == 404


async def test_readers_see_but_do_not_upload(client: AsyncClient, team: Team, page: dict) -> None:
    await publish(client, team, page["id"])
    r = await client.post(
        f"{API}/nodes/{page['id']}/assets",
        headers=team.member.headers,
        files={"file": ("x.png", png(10, 10))},
    )
    assert r.status_code == 403
    uploaded = await _upload(client, team, page, "x.png", png(10, 10))
    await client.delete(f"{API}/nodes/{page['id']}", headers=team.instance.headers)
    gone = await client.get(uploaded.json()["url"], headers=team.member.headers)
    assert gone.status_code == 404
