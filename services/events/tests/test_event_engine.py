import uuid
from datetime import UTC, datetime, timedelta

from events.core.event_engine import EventEngine
from events.domain.zone import Point, Polygon, Zone
from events.infra.polygon_zone_engine import PolygonZoneEngine
from sentinel_common.schemas.detection import BoundingBox, Detection, Velocity
from sentinel_common.schemas.event import EventType

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
OTHER_CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _dock_zone(camera_id: uuid.UUID = CAMERA_ID) -> Zone:
    return Zone(
        id=uuid.uuid4(),
        warehouse_id=WAREHOUSE_ID,
        camera_id=camera_id,
        name="Loading Dock",
        polygon=Polygon(
            points=[
                Point(x=0, y=0),
                Point(x=1000, y=0),
                Point(x=1000, y=1000),
                Point(x=0, y=1000),
            ]
        ),
    )


def _detection(
    *,
    camera_id: uuid.UUID = CAMERA_ID,
    track_id: int | None = 1,
    label: str = "forklift",
    x_min: float = 10.0,
    y_min: float = 10.0,
    size: float = 10.0,
    velocity: Velocity | None = None,
) -> Detection:
    return Detection(
        camera_id=camera_id,
        captured_at=T0,
        label=label,
        confidence=0.9,
        bounding_box=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_min + size, y_max=y_min + size),
        track_id=track_id,
        velocity=velocity,
    )


def _engine(*, zones: list[Zone] | None = None, **overrides: object) -> EventEngine:
    zone_engine = PolygonZoneEngine(zones if zones is not None else [_dock_zone()])
    return EventEngine(zone_engine, **overrides)


def test_object_entering_a_zone_emits_a_strongly_typed_zone_entered_event() -> None:
    zone = _dock_zone()
    engine = _engine(zones=[zone])

    events = engine.update(T0, [_detection(label="forklift", track_id=1)])

    assert len(events) == 1
    event = events[0]
    assert event.event_type is EventType.ZONE_ENTERED
    assert event.summary == "Forklift entered Loading Dock"
    assert event.camera_id == CAMERA_ID
    assert event.track_id == 1
    assert event.zone_id == zone.id
    assert event.zone_name == "Loading Dock"
    assert event.dwell_time_seconds is None


def test_object_exiting_a_zone_emits_zone_exited_with_dwell_time() -> None:
    engine = _engine()

    engine.update(T0, [_detection(label="person", track_id=1)])
    engine.update(T0 + timedelta(seconds=5), [_detection(label="person", track_id=1)])
    events = engine.update(
        T0 + timedelta(seconds=8),
        [_detection(label="person", x_min=5000, y_min=5000, track_id=1)],
    )

    assert len(events) == 1
    event = events[0]
    assert event.event_type is EventType.ZONE_EXITED
    assert event.summary == "Person exited Loading Dock"
    assert event.dwell_time_seconds == 5.0


def test_staying_in_the_same_zone_across_ticks_emits_nothing_new() -> None:
    engine = _engine()

    engine.update(T0, [_detection(track_id=1)])
    events = engine.update(T0 + timedelta(seconds=1), [_detection(track_id=1)])

    assert events == []


def test_object_starting_to_move_emits_object_moved() -> None:
    engine = _engine(zones=[])

    engine.update(T0, [_detection(label="pallet", track_id=1, velocity=None)])
    events = engine.update(
        T0 + timedelta(seconds=1),
        [_detection(label="pallet", track_id=1, velocity=Velocity(vx=10.0, vy=0.0))],
    )

    assert len(events) == 1
    event = events[0]
    assert event.event_type is EventType.OBJECT_MOVED
    assert event.summary == "Pallet moved"
    assert event.track_id == 1


def test_object_stopping_emits_object_stopped() -> None:
    engine = _engine(zones=[])

    engine.update(T0, [_detection(label="pallet", track_id=1, velocity=None)])
    engine.update(
        T0 + timedelta(seconds=1),
        [_detection(label="pallet", track_id=1, velocity=Velocity(vx=10.0, vy=0.0))],
    )
    events = engine.update(
        T0 + timedelta(seconds=2),
        [_detection(label="pallet", track_id=1, velocity=Velocity(vx=0.0, vy=0.0))],
    )

    assert len(events) == 1
    assert events[0].event_type is EventType.OBJECT_STOPPED
    assert events[0].summary == "Pallet stopped"


def test_continuing_to_move_does_not_re_emit_object_moved() -> None:
    engine = _engine(zones=[])

    engine.update(T0, [_detection(label="pallet", track_id=1, velocity=None)])
    engine.update(
        T0 + timedelta(seconds=1),
        [_detection(label="pallet", track_id=1, velocity=Velocity(vx=10.0, vy=0.0))],
    )
    events = engine.update(
        T0 + timedelta(seconds=2),
        [_detection(label="pallet", track_id=1, velocity=Velocity(vx=10.0, vy=0.0))],
    )

    assert events == []


def test_pallet_moving_while_overlapping_a_worker_is_a_pick_not_a_plain_move() -> None:
    engine = _engine(zones=[])

    worker = _detection(label="person", track_id=2, x_min=10, y_min=10, size=20)
    pallet_still = _detection(label="pallet", track_id=1, x_min=15, y_min=15, size=5, velocity=None)
    pallet_moving = _detection(
        label="pallet", track_id=1, x_min=15, y_min=15, size=5, velocity=Velocity(vx=10.0, vy=0.0)
    )

    engine.update(T0, [worker, pallet_still])
    events = engine.update(T0 + timedelta(seconds=1), [worker, pallet_moving])

    picked = [e for e in events if e.event_type is EventType.OBJECT_PICKED]
    moved = [e for e in events if e.event_type is EventType.OBJECT_MOVED]
    assert len(picked) == 1
    assert moved == []

    event = picked[0]
    assert event.summary == "Worker picked pallet"
    assert event.track_id == 1
    assert event.related_track_id == 2
    assert event.related_label == "person"


def test_pallet_moving_without_a_nearby_worker_is_a_plain_move() -> None:
    engine = _engine(zones=[])

    far_worker = _detection(label="person", track_id=2, x_min=900, y_min=900, size=20)
    pallet_still = _detection(label="pallet", track_id=1, x_min=15, y_min=15, size=5, velocity=None)
    pallet_moving = _detection(
        label="pallet", track_id=1, x_min=15, y_min=15, size=5, velocity=Velocity(vx=10.0, vy=0.0)
    )

    engine.update(T0, [far_worker, pallet_still])
    events = engine.update(T0 + timedelta(seconds=1), [far_worker, pallet_moving])

    assert len(events) == 1
    assert events[0].event_type is EventType.OBJECT_MOVED
    assert events[0].summary == "Pallet moved"


def test_a_worker_moving_does_not_trigger_a_pick_event_on_itself() -> None:
    engine = _engine(zones=[])

    engine.update(T0, [_detection(label="person", track_id=1, velocity=None)])
    events = engine.update(
        T0 + timedelta(seconds=1),
        [_detection(label="person", track_id=1, velocity=Velocity(vx=10.0, vy=0.0))],
    )

    assert len(events) == 1
    assert events[0].event_type is EventType.OBJECT_MOVED
    assert events[0].summary == "Person moved"


def test_detection_without_track_id_produces_no_motion_events() -> None:
    engine = _engine(zones=[])

    events = engine.update(T0, [_detection(track_id=None, velocity=Velocity(vx=10.0, vy=0.0))])

    assert events == []


def test_different_cameras_are_tracked_independently() -> None:
    zone_a = _dock_zone(camera_id=CAMERA_ID)
    zone_b = _dock_zone(camera_id=OTHER_CAMERA_ID)
    engine = _engine(zones=[zone_a, zone_b])

    events = engine.update(
        T0,
        [
            _detection(camera_id=CAMERA_ID, track_id=1, label="forklift"),
            _detection(camera_id=OTHER_CAMERA_ID, track_id=1, label="pallet"),
        ],
    )

    assert len(events) == 2
    summaries = {e.summary for e in events}
    assert summaries == {"Forklift entered Loading Dock", "Pallet entered Loading Dock"}


def test_events_are_strongly_typed_event_create_instances() -> None:
    engine = _engine()

    events = engine.update(T0, [_detection(track_id=1)])

    assert len(events) == 1
    event = events[0]
    assert isinstance(event.occurred_at, datetime)
    assert isinstance(event.event_type, EventType)
