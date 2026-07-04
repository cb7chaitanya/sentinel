"""ByteTrack-style implementation of `domain.tracker.ObjectTracker`.

ByteTrack's key idea over a plain IoU tracker (SORT): don't throw away
low-confidence detections. A real object mid-occlusion or motion blur often
only clears a low confidence threshold, not a high one. So matching happens
in two passes each frame:

  1. Match active tracks against *high*-confidence detections by IoU.
  2. Match tracks still unmatched after (1) against *low*-confidence
     detections -- this recovers tracks a plain tracker would drop.

Only unmatched *high*-confidence detections spawn new tracks; unmatched
low-confidence detections are discarded (they're too noisy to trust as a
brand-new object, only as a continuation of one already being tracked).
Tracks that stay unmatched for more than `max_missed_frames` are dropped.

Matching itself is greedy: candidate (track, detection) pairs are sorted by
IoU descending and assigned first-come-first-served. This is simpler and
dependency-free compared to an optimal Hungarian assignment (as in
`scipy.optimize.linear_sum_assignment`); swapping one in later would only
touch `_greedy_iou_match` below, not the public `ObjectTracker` Protocol.

Motion (for `velocity`) is a simple finite difference between the last two
observed bounding-box centers -- enough to satisfy the domain contract
without pulling in a full Kalman filter. That, too, is an internal
implementation detail a future revision could upgrade without changing the
Protocol.
"""

import uuid
from datetime import datetime

from sentinel_common.schemas.detection import BoundingBox, Detection, Velocity

from vision.domain.detector import RawDetection
from vision.domain.tracker import ObjectTracker


def _center(box: BoundingBox) -> tuple[float, float]:
    return ((box.x_min + box.x_max) / 2.0, (box.y_min + box.y_max) / 2.0)


def _iou(a: BoundingBox, b: BoundingBox) -> float:
    x_min = max(a.x_min, b.x_min)
    y_min = max(a.y_min, b.y_min)
    x_max = min(a.x_max, b.x_max)
    y_max = min(a.y_max, b.y_max)

    intersection = max(0.0, x_max - x_min) * max(0.0, y_max - y_min)
    if intersection <= 0.0:
        return 0.0

    area_a = (a.x_max - a.x_min) * (a.y_max - a.y_min)
    area_b = (b.x_max - b.x_min) * (b.y_max - b.y_min)
    union = area_a + area_b - intersection
    return intersection / union if union > 0.0 else 0.0


class _Track:
    """Mutable per-object tracking state. Internal to this module."""

    def __init__(self, track_id: int, detection: RawDetection, timestamp: datetime) -> None:
        self.track_id = track_id
        self.label = detection.label
        self.confidence = detection.confidence
        self.bounding_box = detection.bounding_box
        self.velocity: Velocity | None = None
        self.missed_frames = 0
        self._last_center = _center(detection.bounding_box)
        self._last_seen_at = timestamp

    def update(self, detection: RawDetection, timestamp: datetime) -> None:
        new_center = _center(detection.bounding_box)
        elapsed = (timestamp - self._last_seen_at).total_seconds()
        if elapsed > 0:
            self.velocity = Velocity(
                vx=(new_center[0] - self._last_center[0]) / elapsed,
                vy=(new_center[1] - self._last_center[1]) / elapsed,
            )

        self.label = detection.label
        self.confidence = detection.confidence
        self.bounding_box = detection.bounding_box
        self.missed_frames = 0
        self._last_center = new_center
        self._last_seen_at = timestamp


def _greedy_iou_match(
    track_ids: list[int],
    tracks: dict[int, _Track],
    detections: list[RawDetection],
    iou_threshold: float,
) -> tuple[list[tuple[int, RawDetection]], list[int], list[RawDetection]]:
    """Greedily pair tracks with detections by descending IoU.

    Returns (matches, unmatched_track_ids, unmatched_detections).
    """
    candidates: list[tuple[float, int, int]] = []
    for track_id in track_ids:
        track_box = tracks[track_id].bounding_box
        for det_index, detection in enumerate(detections):
            iou = _iou(track_box, detection.bounding_box)
            if iou >= iou_threshold:
                candidates.append((iou, track_id, det_index))

    candidates.sort(key=lambda c: c[0], reverse=True)

    matched_tracks: set[int] = set()
    matched_detections: set[int] = set()
    matches: list[tuple[int, RawDetection]] = []

    for _iou_score, track_id, det_index in candidates:
        if track_id in matched_tracks or det_index in matched_detections:
            continue
        matches.append((track_id, detections[det_index]))
        matched_tracks.add(track_id)
        matched_detections.add(det_index)

    unmatched_tracks = [t for t in track_ids if t not in matched_tracks]
    unmatched_detections = [d for i, d in enumerate(detections) if i not in matched_detections]
    return matches, unmatched_tracks, unmatched_detections


class ByteTracker(ObjectTracker):
    """Tracks objects for a single camera stream. Not thread-safe; call
    `update()` sequentially from one consumer per instance."""

    def __init__(
        self,
        camera_id: uuid.UUID,
        *,
        high_confidence_threshold: float,
        low_confidence_threshold: float,
        iou_threshold: float,
        max_missed_frames: int,
    ) -> None:
        self._camera_id = camera_id
        self._high_confidence_threshold = high_confidence_threshold
        self._low_confidence_threshold = low_confidence_threshold
        self._iou_threshold = iou_threshold
        self._max_missed_frames = max_missed_frames
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    def update(self, timestamp: datetime, detections: list[RawDetection]) -> list[Detection]:
        high_confidence = [
            d for d in detections if d.confidence >= self._high_confidence_threshold
        ]
        low_confidence = [
            d
            for d in detections
            if self._low_confidence_threshold <= d.confidence < self._high_confidence_threshold
        ]

        active_track_ids = list(self._tracks.keys())
        updated_track_ids: set[int] = set()

        matches, unmatched_tracks, unmatched_high = _greedy_iou_match(
            active_track_ids, self._tracks, high_confidence, self._iou_threshold
        )
        for track_id, detection in matches:
            self._tracks[track_id].update(detection, timestamp)
            updated_track_ids.add(track_id)

        recovered, still_unmatched, _unmatched_low = _greedy_iou_match(
            unmatched_tracks, self._tracks, low_confidence, self._iou_threshold
        )
        for track_id, detection in recovered:
            self._tracks[track_id].update(detection, timestamp)
            updated_track_ids.add(track_id)

        for detection in unmatched_high:
            track_id = self._next_track_id
            self._next_track_id += 1
            self._tracks[track_id] = _Track(track_id, detection, timestamp)
            updated_track_ids.add(track_id)

        for track_id in still_unmatched:
            track = self._tracks[track_id]
            track.missed_frames += 1
            if track.missed_frames > self._max_missed_frames:
                del self._tracks[track_id]

        detections_out = [
            self._to_detection(self._tracks[tid], timestamp) for tid in updated_track_ids
        ]
        detections_out.sort(key=lambda detection: detection.track_id or 0)
        return detections_out

    def _to_detection(self, track: _Track, timestamp: datetime) -> Detection:
        return Detection(
            camera_id=self._camera_id,
            captured_at=timestamp,
            label=track.label,
            confidence=track.confidence,
            bounding_box=track.bounding_box,
            track_id=track.track_id,
            velocity=track.velocity,
        )


class ByteTrackerFactory:
    """Builds `ByteTracker`s using the process's tracking settings."""

    def __init__(
        self,
        *,
        high_confidence_threshold: float,
        low_confidence_threshold: float,
        iou_threshold: float,
        max_missed_frames: int,
    ) -> None:
        self._high_confidence_threshold = high_confidence_threshold
        self._low_confidence_threshold = low_confidence_threshold
        self._iou_threshold = iou_threshold
        self._max_missed_frames = max_missed_frames

    def create(self, camera_id: uuid.UUID) -> ObjectTracker:
        return ByteTracker(
            camera_id,
            high_confidence_threshold=self._high_confidence_threshold,
            low_confidence_threshold=self._low_confidence_threshold,
            iou_threshold=self._iou_threshold,
            max_missed_frames=self._max_missed_frames,
        )
