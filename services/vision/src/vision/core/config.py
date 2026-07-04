"""Vision service settings.

`min_confidence` is a floor, not a display threshold: it's passed to YOLO
as its inference-time confidence cutoff *and* used as ByteTrack's
low-confidence threshold, so nothing the tracker might still want is
discarded before it ever reaches it. `tracker_high_confidence_threshold`
is the point above which a detection is trusted enough to start a brand
new track; see `infra/byte_tracker.py` for why the split matters.
"""

from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "vision"
    port: int = 8002

    model_weights_path: str = "yolov8n.pt"
    min_confidence: float = 0.1
    device: str = "cpu"

    tracker_high_confidence_threshold: float = 0.6
    tracker_iou_threshold: float = 0.3
    tracker_max_missed_frames: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
