"""Schemas describing detections produced by the vision service.

`Detection` is the fully-assembled, per-object output of the detect+track
pipeline (see `services/vision`): every instance already carries a stable
`track_id` and, once a track has more than one observation, its `velocity`.
`FrameDetections` is the structured result for one captured frame -- the
unit the vision service actually produces.
"""

import uuid
from datetime import datetime

from pydantic import Field

from sentinel_common.schemas.common import SentinelModel


class BoundingBox(SentinelModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class Velocity(SentinelModel):
    """Estimated motion of a tracked object's bounding-box center, in pixels/second."""

    vx: float
    vy: float


class Detection(SentinelModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    camera_id: uuid.UUID
    captured_at: datetime
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    track_id: int | None = None
    velocity: Velocity | None = None


class FrameDetections(SentinelModel):
    """All detections produced for a single captured frame."""

    camera_id: uuid.UUID
    timestamp: datetime
    detections: list[Detection] = []
