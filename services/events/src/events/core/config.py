from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "events"
    port: int = 8003

    dwell_time_threshold_seconds: int = 30
    memory_service_url: str = "http://memory:8004"


@lru_cache
def get_settings() -> Settings:
    return Settings()
