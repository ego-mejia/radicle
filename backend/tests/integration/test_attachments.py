import io
import time

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.config import get_settings
from radicle.services import attachments as service
from tests.conftest import Team, new_ticket, run_jobs

API = "/api/v1"


def png(width: int, height: int, *, exif_orientation: int | None = None, fmt: str = "PNG") -> bytes:
    image = Image.new("RGB", (width, height), (200, 240, 50))
    for x in range(0, width, 7):
        for y in range(0, height, 13):
            image.putpixel((x, y), ((x * 3) % 255, (y * 5) % 255, (x + y) % 255))
    out = io.BytesIO()
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation  # Orientation
        exif[0x010F] = "Phone maker"  # Make: private metadata
        image.save(out, "JPEG", exif=exif.tobytes(), quality=95)
    else:
        image.save(out, fmt)
    return out.getvalue()


async def upload(client: AsyncClient, actor, key: str, name: str, data: bytes, **form: str):  # type: ignore[no-untyped-def]
    return await client.post(
        f"{API}/tickets/{key}/attachments",
        headers=actor.headers,
        files={"file": (name, data)},
        data=form,
    )


async def fetch(client: AsyncClient, url: str, headers: dict | None = None):  # type: ignore[no-untyped-def]
    return await client.get(url, headers=headers or {})


async def test_acceptance_screenshot_in_comment_resized_to_medium(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    await new_ticket(client, board.member)
    r = await client.post(
        f"{API}/tickets/PA-1/comments", headers=board.member.headers, json={"body_md": "Mira:"}
    )
    comment_id = r.json()["id"]
    shot = png(2400, 1500)
    r = await upload(client, board.member, "PA-1", "screenshot.png", shot, comment_id=comment_id)
    assert r.status_code == 201, r.text
    attachment = r.json()
    assert attachment["mime_type"] == "image/png"
    assert (attachment["width"], attachment["height"]) == (2048, 1280)  # default large
    assert attachment["comment_id"] == comment_id
    assert attachment["markdown"] == f"![screenshot.png](attachment:{attachment['id']})"
    assert attachment["preview_url"] is None  # the worker has not run yet

    assert await run_jobs(db) == ["attachment_variants"]
    listed = (
        await client.get(f"{API}/tickets/PA-1/attachments", headers=board.viewer.headers)
    ).json()
    item = listed["items"][0]
    preview = await fetch(client, item["preview_url"])
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/webp"
    assert Image.open(io.BytesIO(preview.content)).size == (1280, 800)
    thumb = await fetch(client, item["thumb_url"])
    assert Image.open(io.BytesIO(thumb.content)).size == (320, 200)

    before = item["size_bytes"]
    r = await client.post(
        f"{API}/attachments/{item['id']}/resize",
        headers=board.member.headers,
        json={"preset": "medium"},
    )
    assert r.status_code == 200, r.text
    assert (r.json()["width"], r.json()["height"]) == (1280, 800)
    assert r.json()["size_bytes"] < before
    original = await fetch(client, r.json()["url"])
    assert len(original.content) == r.json()["size_bytes"]

    r = await client.post(
        f"{API}/attachments/{item['id']}/resize",
        headers=board.member.headers,
        json={"preset": "large"},
    )
    assert r.status_code == 409 and "never enlarged" in r.json()["detail"]
    history = (await client.get(f"{API}/tickets/PA-1/history", headers=board.member.headers)).json()
    kinds = [e["event_type"] for e in history["items"]]
    assert kinds[:2] == ["attachment_resized", "attachment_added"]


@pytest.mark.parametrize(
    ("preset", "size"),
    [
        ("original", (3000, 1000)),
        ("large", (2048, 683)),
        ("medium", (1280, 427)),
        ("small", (800, 267)),
    ],
)
async def test_presets(
    client: AsyncClient, board: Team, preset: str, size: tuple[int, int]
) -> None:
    await new_ticket(client, board.member)
    r = await upload(client, board.member, "PA-1", "wide.png", png(3000, 1000), resize=preset)
    assert (r.json()["width"], r.json()["height"]) == size


async def test_exif_is_stripped_and_orientation_applied(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    photo = png(600, 300, exif_orientation=6)  # rotated 90° on display
    assert Image.open(io.BytesIO(photo)).getexif()
    r = await upload(client, board.member, "PA-1", "photo.jpg", photo)
    body = r.json()
    assert body["mime_type"] == "image/jpeg"
    assert (body["width"], body["height"]) == (300, 600)
    stored = await fetch(client, body["url"])
    assert not Image.open(io.BytesIO(stored.content)).getexif()


async def test_type_comes_from_the_content(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await upload(client, board.member, "PA-1", "notes.txt", png(10, 10))
    assert r.json()["mime_type"] == "image/png" and r.json()["is_image"] is True
    r = await upload(client, board.member, "PA-1", "fake.png", b"hola\nmundo")
    assert r.json()["mime_type"] == "text/plain" and r.json()["is_image"] is False
    assert r.json()["markdown"].startswith("[fake.png](")
    r = await upload(client, board.member, "PA-1", "data.bin", b'{"a": 1}')
    assert r.json()["mime_type"] == "application/json"
    r = await upload(client, board.member, "PA-1", "blob", bytes(range(256)) * 4)
    assert r.json()["mime_type"] == "application/octet-stream"
    download = await fetch(client, r.json()["url"])
    assert download.headers["content-disposition"].startswith("attachment;")
    r = await upload(client, board.member, "PA-1", "empty.txt", b"")
    assert r.status_code == 422


async def test_size_limit(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    await new_ticket(client, board.member)
    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    r = await upload(client, board.member, "PA-1", "big.bin", b"x" * (1024 * 1024 + 1))
    assert r.status_code == 413
    assert r.json()["detail"] == "The file is 1.0 MB; the limit is 1 MB."
    r = await upload(client, board.member, "PA-1", "ok.txt", b"x" * 1000)
    assert r.status_code == 201


async def test_signed_urls_expire(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await upload(client, board.member, "PA-1", "a.txt", b"secreto")
    attachment_id = r.json()["id"]
    url = r.json()["url"]
    client.cookies.clear()
    assert (await fetch(client, url)).content == b"secreto"  # signature, no auth
    import uuid

    old = service.signed_query(uuid.UUID(attachment_id), "original", now=time.time() - 3600)
    r = await fetch(client, f"{API}/attachments/{attachment_id}/content?{old}")
    assert r.status_code == 401 and "expired" in r.json()["detail"]
    r = await fetch(client, f"{API}/attachments/{attachment_id}/content")
    assert r.status_code == 401
    r = await fetch(client, f"{API}/attachments/{attachment_id}/content", board.viewer.headers)
    assert r.content == b"secreto"
    r = await fetch(client, f"{API}/attachments/{attachment_id}/content", board.outsider.headers)
    assert r.status_code == 404
    tampered = url.replace("variant=original", "variant=thumb")
    assert (await fetch(client, tampered)).status_code == 401


async def test_permissions_and_delete(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await upload(client, board.viewer, "PA-1", "a.txt", b"x")
    assert r.status_code == 403
    r = await upload(client, board.outsider, "PA-1", "a.txt", b"x")
    assert r.status_code == 404
    first = (await upload(client, board.member, "PA-1", "a.txt", b"x")).json()
    second = (await upload(client, board.member, "PA-1", "b.txt", b"y")).json()
    r = await client.delete(f"{API}/attachments/{first['id']}", headers=board.agent.headers)
    assert r.status_code == 403 and "attachment.delete_any" in r.json()["detail"]
    assert (
        await client.delete(f"{API}/attachments/{first['id']}", headers=board.member.headers)
    ).status_code == 204
    assert (
        await client.delete(f"{API}/attachments/{second['id']}", headers=board.admin.headers)
    ).status_code == 204
    r = await client.get(f"{API}/tickets/PA-1", headers=board.member.headers)
    assert r.json()["attachments"] == []
    r = await fetch(client, f"{API}/attachments/{first['id']}/content", board.member.headers)
    assert r.status_code == 404
    events = (await client.get(f"{API}/tickets/PA-1/history", headers=board.member.headers)).json()
    assert [e["event_type"] for e in events["items"]][:2] == [
        "attachment_removed",
        "attachment_removed",
    ]


async def test_resize_errors_and_bad_comment(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    text = (await upload(client, board.member, "PA-1", "a.txt", b"x")).json()
    r = await client.post(
        f"{API}/attachments/{text['id']}/resize",
        headers=board.member.headers,
        json={"preset": "small"},
    )
    assert r.status_code == 422 and "Only images" in r.json()["detail"]
    image = (await upload(client, board.member, "PA-1", "a.png", png(900, 900))).json()
    r = await client.post(
        f"{API}/attachments/{image['id']}/resize",
        headers=board.member.headers,
        json={"preset": "huge"},
    )
    assert r.status_code == 422
    r = await upload(client, board.member, "PA-1", "a.png", png(10, 10), resize="huge")
    assert r.status_code == 422 and "Unknown size" in r.json()["detail"]
    r = await client.post(
        f"{API}/tickets/PA-2/comments", headers=board.member.headers, json={"body_md": "otro"}
    )
    r = await upload(client, board.member, "PA-1", "a.txt", b"x", comment_id=r.json()["id"])
    assert r.status_code == 422 and "comment_id" in r.json()["detail"]
    r = await upload(client, board.member, "PA-1", "broken.png", b"\x89PNG\r\n\x1a\n" + b"0" * 50)
    assert r.status_code == 422 and "could not be read" in r.json()["detail"]
