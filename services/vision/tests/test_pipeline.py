import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sentinel_common.schemas.detection import BoundingBox, Detection
from sentinel_common.schemas.frame import Frame
from vision.core.pipeline import VisionPipeline
from vision.domain.detector import RawDetection
from vision.domain.tracker import ObjectTracker

CAMERA_ID = uuid.uuid4()
OTHER_CAMERA_ID = uuid.uuid4()
TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)


def _frame(camera_id: uuid.UUID = CAMERA_ID, sequence: int = 1) -> Frame:
    return Frame(
        camera_id=camera_id,
        sequence=sequence,
        captured_at=TIMESTAMP,
        data=b"jpeg-bytes",
        width=640,
        height=480,
    )


class FakeDetector:
    def __init__(self, raw_detections: list[RawDetection]) -> None:
        self.raw_detections = raw_detections
        self.calls: list[Frame] = []

    async def detect(self, frame: Frame) -> list[RawDetection]:
        self.calls.append(frame)
        return self.raw_detections


class FakeTracker:
    def __init__(self, camera_id: uuid.UUID) -> None:
        self.camera_id = camera_id
        self.calls: list[tuple[datetime, list[RawDetection]]] = []

    def update(self, timestamp: datetime, detections: list[RawDetection]) -> list[Detection]:
        self.calls.append((timestamp, detections))
        return [
            Detection(
                camera_id=self.camera_id,
                captured_at=timestamp,
                label=d.label,
                confidence=d.confidence,
                bounding_box=d.bounding_box,
                track_id=index + 1,
            )
            for index, d in enumerate(detections)
        ]


class FakeTrackerFactory:
    def __init__(self) -> None:
        self.created_for: list[uuid.UUID] = []
        self.trackers: dict[uuid.UUID, FakeTracker] = {}

    def create(self, camera_id: uuid.UUID) -> ObjectTracker:
        self.created_for.append(camera_id)
        tracker = FakeTracker(camera_id)
        self.trackers[camera_id] = tracker
        return tracker


def _raw_detection() -> RawDetection:
    return RawDetection(
        label="forklift",
        confidence=0.8,
        bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
    )


async def test_process_wires_detector_output_into_tracker() -> None:
    detector = FakeDetector([_raw_detection()])
    factory = FakeTrackerFactory()
    pipeline = VisionPipeline(detector, factory)

    result = await pipeline.process(_frame())

    assert result.camera_id == CAMERA_ID
    assert result.timestamp == TIMESTAMP
    assert len(result.detections) == 1
    assert result.detections[0].track_id == 1
    assert result.detections[0].label == "forklift"

    assert detector.calls == [_frame()]
    tracker = factory.trackers[CAMERA_ID]
    assert tracker.calls == [(TIMESTAMP, [_raw_detection()])]


async def test_process_reuses_the_same_tracker_for_a_camera() -> None:
    detector = FakeDetector([_raw_detection()])
    factory = FakeTrackerFactory()
    pipeline = VisionPipeline(detector, factory)

    await pipeline.process(_frame(sequence=1))
    await pipeline.process(_frame(sequence=2))

    assert factory.created_for == [CAMERA_ID]  # only created once


async def test_process_uses_separate_trackers_per_camera() -> None:
    detector = FakeDetector([_raw_detection()])
    factory = FakeTrackerFactory()
    pipeline = VisionPipeline(detector, factory)

    await pipeline.process(_frame(camera_id=CAMERA_ID))
    await pipeline.process(_frame(camera_id=OTHER_CAMERA_ID))

    assert set(factory.created_for) == {CAMERA_ID, OTHER_CAMERA_ID}


async def test_process_stream_yields_one_result_per_frame() -> None:
    detector = FakeDetector([_raw_detection()])
    factory = FakeTrackerFactory()
    pipeline = VisionPipeline(detector, factory)

    async def frames() -> AsyncIterator[Frame]:
        yield _frame(sequence=1)
        yield _frame(sequence=2)

    results = [result async for result in pipeline.process_stream(frames())]

    assert len(results) == 2
    assert all(r.camera_id == CAMERA_ID for r in results)


async def test_process_produces_empty_detections_when_nothing_is_detected() -> None:
    detector = FakeDetector([])
    factory = FakeTrackerFactory()
    pipeline = VisionPipeline(detector, factory)

    result = await pipeline.process(_frame())

    assert result.camera_id == CAMERA_ID
    assert result.detections == []
