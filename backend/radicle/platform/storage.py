"""Where attachment bytes live: a local directory or any S3-compatible bucket.

Both backends implement the same small interface, chosen by RADICLE_STORAGE.
"""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from radicle.platform.config import Settings, get_settings

PRESIGN_SECONDS = 300


class StorageBackend(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def download_url(self, key: str, filename: str, *, inline: bool) -> str | None:
        """A short-lived direct URL, or None when the API must stream the bytes itself."""
        ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Invalid storage key {key}")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    async def download_url(self, key: str, filename: str, *, inline: bool) -> str | None:
        return None


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.s3_bucket
        self.client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=key)
        body: bytes = await asyncio.to_thread(response["Body"].read)
        return body

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)

    async def download_url(self, key: str, filename: str, *, inline: bool) -> str | None:
        disposition = "inline" if inline else "attachment"
        url: str = await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f"{disposition}; filename*=UTF-8''{quote(filename)}",
            },
            ExpiresIn=PRESIGN_SECONDS,
        )
        return url


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage == "s3":
        return S3Storage(settings)
    if settings.storage != "local":
        raise ValueError(f"RADICLE_STORAGE must be local or s3, not {settings.storage!r}")
    return LocalStorage(settings.storage_dir)
