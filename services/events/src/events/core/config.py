from functools import lru_cache

from sentinel_common.config import BaseServiceSettings

from events.domain.zone import Zone


class Settings(BaseServiceSettings):
    service_name: str = "events"
    port: int = 8003

    dwell_time_threshold_seconds: int = 30
    memory_service_url: str = "http://memory:8004"

    zones: list[Zone] = []
    zone_exit_grace_period_seconds: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
