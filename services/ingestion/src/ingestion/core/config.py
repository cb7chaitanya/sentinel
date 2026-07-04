"""Ingestion service settings.

`camera_sources` fully describes what to capture: every entry names a
camera and whether it's an RTSP stream, a local webcam, or a video file (see
`domain.camera.StreamSource`). The reconnect/backoff knobs apply uniformly
across all three kinds -- see `infra/opencv_capture.py` for why an RTSP
drop, a webcam unplug, and a video file's EOF are handled by the same loop.
"""

from functools import lru_cache

from sentinel_common.config import BaseServiceSettings

from ingestion.domain.camera import StreamSource


class Settings(BaseServiceSettings):
    service_name: str = "ingestion"
    port: int = 8001

    camera_sources: list[StreamSource] = []

    reconnect_initial_backoff_seconds: float = 1.0
    reconnect_max_backoff_seconds: float = 30.0
    max_consecutive_read_failures: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
