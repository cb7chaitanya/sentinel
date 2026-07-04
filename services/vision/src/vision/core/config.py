from functools import lru_cache

from sentinel_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "vision"
    port: int = 8002

    model_weights_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.5
    device: str = "cpu"


@lru_cache
def get_settings() -> Settings:
    return Settings()
