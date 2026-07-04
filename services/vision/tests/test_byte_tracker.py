import uuid
from datetime import UTC, datetime, timedelta

from sentinel_common.schemas.detection import BoundingBox
from vision.domain.detector import RawDetection
from vision.infra.byte_tracker import ByteTracker

CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _box(x_min: float, y_min: float = 0.0, *, size: float = 10.0) -> BoundingBox:
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_min + size, y_max=y_min + size)


def _detection(x_min: float, *, confidence: float = 0.9, label: str = "person") -> RawDetection:
    return RawDetection(label=label, confidence=confidence, bounding_box=_box(x_min))


def _tracker(**overrides: float | int) -> ByteTracker:
    params = {
        "high_confidence_threshold": 0.6,
        "low_confidence_threshold": 0.1,
        "iou_threshold": 0.3,
        "max_missed_frames": 2,
    }
    params.update(overrides)
    return ByteTracker(CAMERA_ID, **params)


def test_first_detection_creates_a_new_track_with_no_velocity() -> None:
    tracker = _tracker()

    detections = tracker.update(T0, [_detection(0)])

    assert len(detections) == 1
    detection = detections[0]
    assert detection.track_id == 1
    assert detection.camera_id == CAMERA_ID
    assert detection.captured_at == T0
    assert detection.velocity is None


def test_same_object_across_frames_keeps_the_same_track_id() -> None:
    tracker = _tracker()

    first = tracker.update(T0, [_detection(0)])
    second = tracker.update(T0 + timedelta(seconds=1), [_detection(1)])  # moved slightly, high IoU

    assert first[0].track_id == second[0].track_id


def test_velocity_is_computed_from_consecutive_observations() -> None:
    tracker = _tracker()

    tracker.update(T0, [_detection(0)])
    # Box (0,0,10,10) -> (5,0,15,10): center moves from (5,5) to (10,5) in 1s,
    # and still overlaps enough (IoU ~0.33) to match the same track.
    detections = tracker.update(T0 + timedelta(seconds=1), [_detection(5)])

    velocity = detections[0].velocity
    assert velocity is not None
    assert velocity.vx == 5.0
    assert velocity.vy == 0.0


def test_distinct_objects_get_distinct_track_ids() -> None:
    tracker = _tracker()

    detections = tracker.update(T0, [_detection(0), _detection(100)])

    track_ids = {d.track_id for d in detections}
    assert len(track_ids) == 2


def test_track_survives_a_low_confidence_recovery_frame() -> None:
    tracker = _tracker()
    tracker.update(T0, [_detection(0, confidence=0.9)])

    # Same position, but only a low-confidence detection this frame (e.g. occlusion).
    recovered = tracker.update(T0 + timedelta(seconds=1), [_detection(0, confidence=0.2)])

    assert len(recovered) == 1
    assert recovered[0].track_id == 1


def test_unmatched_low_confidence_detection_does_not_start_a_new_track() -> None:
    tracker = _tracker()

    detections = tracker.update(T0, [_detection(0, confidence=0.2)])

    assert detections == []


def test_track_is_dropped_after_exceeding_max_missed_frames() -> None:
    tracker = _tracker(max_missed_frames=1)
    tracker.update(T0, [_detection(0)])

    # Two consecutive frames with nothing matching -> exceeds max_missed_frames=1.
    tracker.update(T0 + timedelta(seconds=1), [])
    tracker.update(T0 + timedelta(seconds=2), [])

    # A new detection at the same spot must now start a brand new track.
    detections = tracker.update(T0 + timedelta(seconds=3), [_detection(0)])
    assert detections[0].track_id == 2


def test_track_recovers_within_missed_frame_budget() -> None:
    tracker = _tracker(max_missed_frames=2)
    tracker.update(T0, [_detection(0)])

    tracker.update(T0 + timedelta(seconds=1), [])  # missed once, still within budget

    detections = tracker.update(T0 + timedelta(seconds=2), [_detection(0)])
    assert detections[0].track_id == 1
