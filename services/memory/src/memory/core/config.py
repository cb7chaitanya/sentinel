from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "memory"
    port: int = 8004

    database_url: str = "postgresql+asyncpg://sentinel:sentinel@postgres:5432/sentinel"
    db_pool_size: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
