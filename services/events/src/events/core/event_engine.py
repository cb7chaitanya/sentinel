"""Turns continuous object observations into a deduplicated, strongly-typed
warehouse event stream.

"Continuous object observations" means `update()` is called once per tick
with that tick's tracked `Detection`s; the engine remembers state across
calls -- motion state per object, zone occupancy (delegated to
`ZoneEngine`) -- so it only ever emits an event on an actual state change.
An object that's merely still moving, or still inside a zone, produces
nothing on the next tick: that's what makes "never emit duplicate events"
and "maintain object state" the same discipline, not two separate rules.

Three kinds of event come out of this, deliberately kept simple:

  - Zone transitions ("Forklift entered Loading Dock", "Worker exited
    Loading Dock"): delegated entirely to `ZoneEngine`, which already
    handles enter/exit/dwell time -- this class just labels and phrases
    the transitions it returns.
  - Motion transitions ("Pallet moved" / "<label> stopped"): a track's
    velocity crossing `motion_speed_threshold` is a stationary<->moving
    state change, tracked per (camera_id, track_id) exactly like
    `ZoneEngine` tracks occupancy.
  - Pick events ("Worker picked pallet"): a specialization of "started
    moving" -- if a non-worker object starts moving while its bounding box
    overlaps a worker's, that's a pick, not an unexplained "moved". Only
    one of the two fires per movement-start, so this never doubles up
    with a plain OBJECT_MOVED for the same occurrence.

Deliberately not handled: object-state entries are never evicted, so a
very long-running deployment accumulates one entry per (camera_id,
track_id) ever seen. Given how this is used (per-camera track ids
restart from 1 each process run), that's a slow, bounded-in-practice
leak, not a correctness issue -- adding TTL-based eviction now would be
speculative complexity for a need this task doesn't state.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sentinel_common.schemas.detection import BoundingBox, Detection, Velocity
from sentinel_common.schemas.event import EventCreate, EventType
from sentinel_common.schemas.zone import ZoneTransitionKind

from events.domain.zone_engine import ZoneEngine


def _overlaps(a: BoundingBox, b: BoundingBox) -> bool:
    x_min = max(a.x_min, b.x_min)
    y_min = max(a.y_min, b.y_min)
    x_max = min(a.x_max, b.x_max)
    y_max = min(a.y_max, b.y_max)
    return x_max > x_min and y_max > y_min


def _speed(velocity: Velocity | None) -> float:
    if velocity is None:
        return 0.0
    return (velocity.vx**2 + velocity.vy**2) ** 0.5


@dataclass
class _ObjectState:
    label: str
    is_moving: bool = False


class EventEngine:
    def __init__(
        self,
        zone_engine: ZoneEngine,
        *,
        motion_speed_threshold: float = 5.0,
        worker_labels: Iterable[str] = ("person",),
        worker_display_name: str = "Worker",
    ) -> None:
        self._zone_engine = zone_engine
        self._motion_speed_threshold = motion_speed_threshold
        self._worker_labels = frozenset(worker_labels)
        self._worker_display_name = worker_display_name
        self._object_states: dict[tuple[uuid.UUID, int], _ObjectState] = {}

    def update(self, timestamp: datetime, detections: list[Detection]) -> list[EventCreate]:
        self._remember_labels(detections)

        events: list[EventCreate] = []
        events.extend(self._zone_events(timestamp, detections))
        events.extend(self._motion_events(timestamp, detections))
        return events

    def _remember_labels(self, detections: list[Detection]) -> None:
        for detection in detections:
            if detection.track_id is None:
                continue
            key = (detection.camera_id, detection.track_id)
            state = self._object_states.get(key)
            if state is None:
                self._object_states[key] = _ObjectState(label=detection.label)
            else:
                state.label = detection.label

    def _zone_events(self, timestamp: datetime, detections: list[Detection]) -> list[EventCreate]:
        events: list[EventCreate] = []
        for transition in self._zone_engine.update(timestamp, detections):
            label = self._label_for(transition.camera_id, transition.track_id)
            if transition.kind is ZoneTransitionKind.ENTERED:
                event_type = EventType.ZONE_ENTERED
                summary = f"{label} entered {transition.zone_name}"
            else:
                event_type = EventType.ZONE_EXITED
                summary = f"{label} exited {transition.zone_name}"

            events.append(
                EventCreate(
                    camera_id=transition.camera_id,
                    event_type=event_type,
                    occurred_at=timestamp,
                    summary=summary,
                    warehouse_id=transition.warehouse_id,
                    track_id=transition.track_id,
                    zone_id=transition.zone_id,
                    zone_name=transition.zone_name,
                    dwell_time_seconds=transition.dwell_time_seconds,
                )
            )
        return events

    def _motion_events(self, timestamp: datetime, detections: list[Detection]) -> list[EventCreate]:
        events: list[EventCreate] = []
        for detection in detections:
            if detection.track_id is None:
                continue

            key = (detection.camera_id, detection.track_id)
            state = self._object_states[key]
            is_moving_now = _speed(detection.velocity) >= self._motion_speed_threshold
            if is_moving_now == state.is_moving:
                continue  # no state change -> nothing to emit

            state.is_moving = is_moving_now
            label = self._label_for(detection.camera_id, detection.track_id)
            if is_moving_now:
                worker = self._nearby_worker(detection, detections)
                if worker is not None:
                    events.append(self._picked_event(timestamp, detection, worker))
                else:
                    events.append(
                        EventCreate(
                            camera_id=detection.camera_id,
                            event_type=EventType.OBJECT_MOVED,
                            occurred_at=timestamp,
                            summary=f"{label} moved",
                            track_id=detection.track_id,
                        )
                    )
            else:
                events.append(
                    EventCreate(
                        camera_id=detection.camera_id,
                        event_type=EventType.OBJECT_STOPPED,
                        occurred_at=timestamp,
                        summary=f"{label} stopped",
                        track_id=detection.track_id,
                    )
                )
        return events

    def _nearby_worker(
        self, detection: Detection, all_detections: list[Detection]
    ) -> Detection | None:
        if detection.label in self._worker_labels:
            return None  # workers don't "pick" via their own movement
        for other in all_detections:
            if other.camera_id != detection.camera_id or other.track_id == detection.track_id:
                continue
            if other.label in self._worker_labels and _overlaps(
                detection.bounding_box, other.bounding_box
            ):
                return other
        return None

    def _picked_event(
        self, timestamp: datetime, detection: Detection, worker: Detection
    ) -> EventCreate:
        return EventCreate(
            camera_id=detection.camera_id,
            event_type=EventType.OBJECT_PICKED,
            occurred_at=timestamp,
            summary=f"{self._worker_display_name} picked {detection.label}",
            track_id=detection.track_id,
            related_track_id=worker.track_id,
            related_label=worker.label,
        )

    def _label_for(self, camera_id: uuid.UUID, track_id: int | None) -> str:
        if track_id is None:
            return "Object"
        state = self._object_states.get((camera_id, track_id))
        return state.label.title() if state else "Object"
