from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "memory"
    port: int = 8004

    database_url: str = "postgresql+asyncpg://sentinel:sentinel@postgres:5432/sentinel"
    db_pool_size: int = 5

    # An entity not observed for longer than this doesn't count as part of
    # "current state" -- see EntityRead.is_active.
    entity_staleness_seconds: float = 30.0
    default_recent_events_limit: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
