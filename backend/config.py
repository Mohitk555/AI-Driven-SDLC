"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings — reads from env / .env file."""

    app_name: str = "InsureOS"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://localhost/insure_os"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "CHANGE_ME"
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
