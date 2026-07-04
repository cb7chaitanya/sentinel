"""Ultralytics YOLO-backed implementation of `domain.detector.ObjectDetector`.

Stubbed out: model loading and inference are follow-up work. Keeping the
constructor signature typed now lets `core/di.py` wire this in as a
singleton without changes once the implementation lands.
"""

from sentinel_common.schemas.detection import Detection
from vision.domain.detector import ObjectDetector


class YoloObjectDetector(ObjectDetector):
    def __init__(self, weights_path: str, confidence_threshold: float, device: str) -> None:
        self._weights_path = weights_path
        self._confidence_threshold = confidence_threshold
        self._device = device

    async def detect(self, frame: bytes, camera_id: str) -> list[Detection]:
        raise NotImplementedError
