"""Base configuration shared by every Sentinel service.

Each service defines its own `Settings` subclass in `core/config.py` and
extends this base with service-specific fields. All values are overridable
via environment variables or a `.env` file (see pydantic-settings docs).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "sentinel-service"
    environment: str = "local"

    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"
    log_json: bool = True

    database_url: str | None = None
