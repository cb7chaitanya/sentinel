"""Domain-level interface for multi-object tracking across frames.

`infra/byte_tracker.py` implements `ObjectTracker` using a ByteTrack-style
two-stage IoU association; the pipeline depends only on this abstraction,
so the tracking algorithm can be swapped without touching orchestration.

Tracking is inherently stateful (it holds position history to assign
stable IDs and estimate velocity) and must never mix frames from different
cameras, so each `ObjectTracker` instance is scoped to one camera stream --
build one per camera via `ObjectTrackerFactory`.
"""

import uuid
from datetime import datetime
from typing import Protocol

from sentinel_common.schemas.detection import Detection

from vision.domain.detector import RawDetection


class ObjectTracker(Protocol):
    def update(self, timestamp: datetime, detections: list[RawDetection]) -> list[Detection]:
        """Associate this frame's detections with tracks from previous frames.

        Returns fully-assembled `Detection`s -- each with a fresh `id`, this
        tracker's `camera_id`, `timestamp` as `captured_at`, a stable
        `track_id`, and `velocity` estimated from track history (`None`
        until a track has at least two observations).
        """
        ...


class ObjectTrackerFactory(Protocol):
    """Builds a per-camera `ObjectTracker`."""

    def create(self, camera_id: uuid.UUID) -> ObjectTracker: ...
