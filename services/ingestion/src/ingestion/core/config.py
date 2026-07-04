from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "ingestion"
    port: int = 8001

    rtsp_stream_urls: list[str] = []
    frame_sample_rate_hz: float = 1.0
    reconnect_backoff_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
