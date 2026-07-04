"""Domain-level interface for object detection over a single frame.

`infra/yolo_detector.py` implements this Protocol against Ultralytics YOLO;
the API layer depends only on this abstraction, so the underlying model or
framework can be swapped without touching routes or DI wiring.
"""

from typing import Protocol

from sentinel_common.schemas.detection import Detection


class ObjectDetector(Protocol):
    async def detect(self, frame: bytes, camera_id: str) -> list[Detection]:
        """Run detection over a single encoded frame and return detections."""
        ...
