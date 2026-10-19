from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RADICLE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://radicle:radicle@localhost:5432/radicle"
    base_url: str = "http://localhost:8000"
    timezone: str = "UTC"
    # None means auto: Secure cookies when base_url is https.
    cookie_secure: bool | None = None
    session_days: int = 14
    login_rate_limit_per_minute: int = 10
    log_level: str = "info"
    static_dir: str | None = Field(default=None, description="Built SPA to serve, if any")

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
