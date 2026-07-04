"""Schemas describing a single YOLO detection produced by the vision service."""

import uuid
from datetime import datetime

from pydantic import Field

from sentinel_common.schemas.common import SentinelModel


class BoundingBox(SentinelModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class Detection(SentinelModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    camera_id: uuid.UUID
    captured_at: datetime
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox
    track_id: int | None = None
