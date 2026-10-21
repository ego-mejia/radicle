"""The S3 backend against a real S3-compatible server (Adobe S3Mock), plus the local
backend's path safety. MinIO's public images are no longer published, see ADR 0013."""

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from radicle.platform.config import Settings
from radicle.platform.storage import LocalStorage, S3Storage, get_storage


@pytest.fixture(scope="module")
def s3() -> Iterator[str]:
    container = (
        DockerContainer("adobe/s3mock:3.12.0")
        .with_env("initialBuckets", "radicle")
        .with_exposed_ports(9090)
        .waiting_for(LogMessageWaitStrategy("Started S3MockApplication"))
    )
    with container:
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9090)}"


async def test_s3_put_get_presign_delete(s3: str) -> None:
    storage = S3Storage(
        Settings(
            storage="s3",
            s3_bucket="radicle",
            s3_endpoint=s3,
            s3_access_key="test",
            s3_secret_key="test",
        )
    )
    await storage.put("p/t/a/original", b"hola s3", "text/plain")
    assert await storage.get("p/t/a/original") == b"hola s3"
    url = await storage.download_url("p/t/a/original", "notas de pruebas.txt", inline=False)
    assert url is not None and "X-Amz-Expires=300" in url
    response = await asyncio.to_thread(httpx.get, url)
    assert response.content == b"hola s3"
    assert "attachment" in response.headers["content-disposition"]
    await storage.delete("p/t/a/original")
    with pytest.raises(Exception, match="NoSuchKey"):
        await storage.get("p/t/a/original")


async def test_local_storage_rejects_escaping_keys(tmp_path) -> None:  # type: ignore[no-untyped-def]
    storage = LocalStorage(str(tmp_path))
    await storage.put("a/b", b"1", "text/plain")
    assert await storage.get("a/b") == b"1"
    assert await storage.download_url("a/b", "x", inline=True) is None
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.get("../../etc/passwd")
    await storage.delete("a/b")
    await storage.delete("a/b")  # missing is fine


def test_storage_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    from radicle.platform import config

    get_storage.cache_clear()
    monkeypatch.setattr(config, "get_settings", lambda: Settings(storage="ftp"))
    monkeypatch.setattr("radicle.platform.storage.get_settings", lambda: Settings(storage="ftp"))
    with pytest.raises(ValueError, match="local or s3"):
        get_storage()
    monkeypatch.setattr("radicle.platform.storage.get_settings", lambda: Settings(storage="s3"))
    get_storage.cache_clear()
    assert isinstance(get_storage(), S3Storage)
    get_storage.cache_clear()
