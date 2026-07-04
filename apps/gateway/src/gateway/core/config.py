from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "gateway"
    port: int = 8000

    # Downstream service base URLs, injected via environment/.env.
    ingestion_service_url: str = "http://ingestion:8001"
    vision_service_url: str = "http://vision:8002"
    events_service_url: str = "http://events:8003"
    memory_service_url: str = "http://memory:8004"
    agent_service_url: str = "http://agent:8005"

    # How often the warehouse-state WebSocket relay re-polls memory for
    # each warehouse with at least one connected subscriber.
    warehouse_state_poll_interval_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
