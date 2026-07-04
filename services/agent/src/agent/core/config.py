from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "agent"
    port: int = 8005

    anthropic_api_key: str | None = None
    agent_model: str = "claude-opus-4-8"
    memory_service_url: str = "http://memory:8004"


@lru_cache
def get_settings() -> Settings:
    return Settings()
