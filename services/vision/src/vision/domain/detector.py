"""Domain-level interface for object detection over a single frame.

`infra/yolo_detector.py` implements this Protocol against Ultralytics YOLO;
the pipeline depends only on this abstraction, so the underlying model or
framework can be swapped without touching orchestration or DI wiring.
"""

from typing import Protocol

from pydantic import Field
from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.detection import BoundingBox
from sentinel_common.schemas.frame import Frame


class RawDetection(SentinelModel):
    """A single detection before tracking has assigned it a stable identity.

    Deliberately has no `id`/`track_id`/`camera_id`/`velocity` -- those are
    the tracker's responsibility to assemble (see `domain/tracker.py`).
    """

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox


class ObjectDetector(Protocol):
    async def detect(self, frame: Frame) -> list[RawDetection]:
        """Run detection over a single frame. No tracking/IDs assigned yet."""
        ...
