"""Runs frames through detection + tracking to produce structured detections.

This is the whole of the vision service's job: consume frames, run YOLO,
run ByteTrack, assign stable IDs, output structured `FrameDetections`. No
HTTP surface -- callers (a future worker process, a test, another service
composed in-process) drive it directly with frames from the ingestion
service's `StreamReader.frames()` or any other `AsyncIterator[Frame]`.

Depends only on the `ObjectDetector`/`ObjectTrackerFactory` domain
Protocols, so the model and tracking algorithm are both swappable without
touching this orchestration.
"""

import uuid
from collections.abc import AsyncIterator

from sentinel_common.schemas.detection import FrameDetections
from sentinel_common.schemas.frame import Frame

from vision.domain.detector import ObjectDetector
from vision.domain.tracker import ObjectTracker, ObjectTrackerFactory


class VisionPipeline:
    def __init__(self, detector: ObjectDetector, tracker_factory: ObjectTrackerFactory) -> None:
        self._detector = detector
        self._tracker_factory = tracker_factory
        self._trackers: dict[uuid.UUID, ObjectTracker] = {}

    async def process(self, frame: Frame) -> FrameDetections:
        """Run one frame through detection + tracking."""
        raw_detections = await self._detector.detect(frame)
        tracker = self._tracker_for(frame.camera_id)
        detections = tracker.update(frame.captured_at, raw_detections)
        return FrameDetections(
            camera_id=frame.camera_id,
            timestamp=frame.captured_at,
            detections=detections,
        )

    async def process_stream(self, frames: AsyncIterator[Frame]) -> AsyncIterator[FrameDetections]:
        """Run a continuous stream of frames through detection + tracking."""
        async for frame in frames:
            yield await self.process(frame)

    def _tracker_for(self, camera_id: uuid.UUID) -> ObjectTracker:
        # Tracking is stateful per camera -- frames from different cameras
        # must never share a tracker instance, or track IDs and velocity
        # would be computed across unrelated streams.
        tracker = self._trackers.get(camera_id)
        if tracker is None:
            tracker = self._tracker_factory.create(camera_id)
            self._trackers[camera_id] = tracker
        return tracker
