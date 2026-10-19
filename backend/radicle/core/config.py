from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RADICLE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://radicle:radicle@localhost:5432/radicle"
    base_url: str = "http://localhost:8000"
    timezone: str = "UTC"
    # Working days for burndowns, e.g. "mon,tue,wed,thu,fri".
    workdays: str = "mon,tue,wed,thu,fri"
    audit_retention_days: int = 730
    # None means auto: Secure cookies when base_url is https.
    cookie_secure: bool | None = None
    session_days: int = 14
    login_rate_limit_per_minute: int = 10
    log_level: str = "info"
    static_dir: str | None = Field(default=None, description="Built SPA to serve, if any")
    # Signs attachment URLs. Without it a key is derived from the database URL.
    secret_key: str | None = None
    storage: str = "local"  # local or s3
    storage_dir: str = "/data/attachments"
    s3_bucket: str = "radicle"
    s3_endpoint: str | None = None  # MinIO, R2...; empty for AWS
    s3_region: str = "us-east-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    max_upload_mb: int = 25
    image_default_resize: str = "large"

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.base_url.startswith("https://")

    @property
    def signing_key(self) -> bytes:
        import hashlib

        base = self.secret_key or f"radicle:{self.database_url}"
        return hashlib.sha256(base.encode()).digest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
