import uuid
from datetime import UTC, datetime, timedelta

from events.domain.zone import Point, Polygon, Zone
from events.infra.polygon_zone_engine import PolygonZoneEngine
from sentinel_common.schemas.detection import BoundingBox, Detection
from sentinel_common.schemas.zone import ZoneTransitionKind

WAREHOUSE_A = uuid.uuid4()
WAREHOUSE_B = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
OTHER_CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _square_zone(
    *,
    zone_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID = WAREHOUSE_A,
    camera_id: uuid.UUID = CAMERA_ID,
    name: str = "Dock",
    x_min: float = 0.0,
    size: float = 100.0,
) -> Zone:
    return Zone(
        id=zone_id or uuid.uuid4(),
        warehouse_id=warehouse_id,
        camera_id=camera_id,
        name=name,
        polygon=Polygon(
            points=[
                Point(x=x_min, y=0),
                Point(x=x_min + size, y=0),
                Point(x=x_min + size, y=size),
                Point(x=x_min, y=size),
            ]
        ),
    )


def _detection(
    *,
    camera_id: uuid.UUID = CAMERA_ID,
    track_id: int | None = 1,
    x_min: float = 10.0,
    y_min: float = 10.0,
    size: float = 10.0,
) -> Detection:
    return Detection(
        camera_id=camera_id,
        captured_at=T0,
        label="person",
        confidence=0.9,
        bounding_box=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_min + size, y_max=y_min + size),
        track_id=track_id,
    )


def test_object_entering_a_zone_emits_an_entered_transition() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone])

    transitions = engine.update(T0, [_detection()])

    assert len(transitions) == 1
    transition = transitions[0]
    assert transition.kind is ZoneTransitionKind.ENTERED
    assert transition.zone_id == zone.id
    assert transition.zone_name == zone.name
    assert transition.warehouse_id == WAREHOUSE_A
    assert transition.camera_id == CAMERA_ID
    assert transition.track_id == 1
    assert transition.dwell_time_seconds is None


def test_object_staying_inside_does_not_re_emit_entered() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone])

    engine.update(T0, [_detection()])
    transitions = engine.update(T0 + timedelta(seconds=1), [_detection()])

    assert transitions == []


def test_object_leaving_the_polygon_emits_exited_with_dwell_time() -> None:
    zone = _square_zone(size=100.0)
    engine = PolygonZoneEngine([zone])

    engine.update(T0, [_detection(x_min=10, y_min=10)])
    engine.update(T0 + timedelta(seconds=5), [_detection(x_min=10, y_min=10)])
    # Move far outside the 100x100 zone.
    transitions = engine.update(T0 + timedelta(seconds=8), [_detection(x_min=500, y_min=500)])

    assert len(transitions) == 1
    transition = transitions[0]
    assert transition.kind is ZoneTransitionKind.EXITED
    assert transition.dwell_time_seconds == 5.0  # last confirmed inside at T0+5s, entered at T0


def test_object_disappearing_from_detections_entirely_eventually_exits() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone], exit_grace_period_seconds=0.0)

    engine.update(T0, [_detection()])
    # Object vanishes from the frame entirely (e.g. left camera view) --
    # not just "outside the polygon", but absent from detections at all.
    transitions = engine.update(T0 + timedelta(seconds=1), [])

    assert len(transitions) == 1
    assert transitions[0].kind is ZoneTransitionKind.EXITED


def test_grace_period_tolerates_a_brief_disappearance() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone], exit_grace_period_seconds=2.0)

    engine.update(T0, [_detection()])
    # Missing for 1s -- within the 2s grace period, should not exit yet.
    transitions = engine.update(T0 + timedelta(seconds=1), [])
    assert transitions == []

    # Reappears inside the zone -- no spurious re-entry, track continues.
    transitions = engine.update(T0 + timedelta(seconds=1.5), [_detection()])
    assert transitions == []

    occupants = engine.current_occupants(zone.id)
    assert len(occupants) == 1
    assert occupants[0].entered_at == T0


def test_grace_period_eventually_expires() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone], exit_grace_period_seconds=2.0)

    engine.update(T0, [_detection()])
    engine.update(T0 + timedelta(seconds=1), [])  # missing, within grace
    transitions = engine.update(T0 + timedelta(seconds=3.5), [])  # 3.5s since last confirmed

    assert len(transitions) == 1
    assert transitions[0].kind is ZoneTransitionKind.EXITED
    assert transitions[0].dwell_time_seconds == 0.0  # only ever confirmed at T0 itself


def test_current_occupants_reports_running_dwell_time() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone])

    engine.update(T0, [_detection()])
    engine.update(T0 + timedelta(seconds=4), [_detection()])

    occupants = engine.current_occupants(zone.id)
    assert len(occupants) == 1
    assert occupants[0].track_id == 1
    assert occupants[0].entered_at == T0
    assert occupants[0].dwell_time_seconds == 4.0


def test_current_occupants_is_empty_after_exit() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone])

    engine.update(T0, [_detection()])
    engine.update(T0 + timedelta(seconds=1), [])

    assert engine.current_occupants(zone.id) == []


def test_detection_without_a_track_id_is_ignored() -> None:
    zone = _square_zone()
    engine = PolygonZoneEngine([zone])

    transitions = engine.update(T0, [_detection(track_id=None)])

    assert transitions == []
    assert engine.current_occupants(zone.id) == []


def test_multiple_tracks_in_the_same_zone_are_independent() -> None:
    zone = _square_zone(size=100.0)
    engine = PolygonZoneEngine([zone])

    engine.update(T0, [_detection(track_id=1, x_min=10), _detection(track_id=2, x_min=20)])
    # Only track 1 leaves.
    transitions = engine.update(
        T0 + timedelta(seconds=1),
        [_detection(track_id=1, x_min=500), _detection(track_id=2, x_min=20)],
    )

    assert len(transitions) == 1
    assert transitions[0].track_id == 1
    assert transitions[0].kind is ZoneTransitionKind.EXITED

    remaining = engine.current_occupants(zone.id)
    assert len(remaining) == 1
    assert remaining[0].track_id == 2


def test_overlapping_zones_are_evaluated_independently() -> None:
    small_zone = _square_zone(name="Inner", size=20.0)
    large_zone = _square_zone(name="Outer", zone_id=uuid.uuid4(), size=100.0)
    engine = PolygonZoneEngine([small_zone, large_zone])

    # A point inside both the small and the large zone.
    transitions = engine.update(T0, [_detection(x_min=5, y_min=5, size=1.0)])

    zone_names = {t.zone_name for t in transitions}
    assert zone_names == {"Inner", "Outer"}


def test_same_zone_name_in_different_warehouses_is_isolated() -> None:
    zone_a = _square_zone(name="Dock", warehouse_id=WAREHOUSE_A, camera_id=CAMERA_ID)
    zone_b = _square_zone(name="Dock", warehouse_id=WAREHOUSE_B, camera_id=OTHER_CAMERA_ID)
    # A generous grace period so warehouse A's occupant doesn't exit for
    # simply not being reconfirmed this tick -- isolation, not timing, is
    # what this test is checking.
    engine = PolygonZoneEngine([zone_a, zone_b], exit_grace_period_seconds=10.0)

    engine.update(T0, [_detection(camera_id=CAMERA_ID, track_id=1)])
    # Same track_id (1) as warehouse A -- track ids are only unique within
    # one camera's stream, so this must not be confused with warehouse A's.
    transitions = engine.update(
        T0 + timedelta(seconds=1),
        [_detection(camera_id=OTHER_CAMERA_ID, track_id=1)],
    )

    entered = [t for t in transitions if t.kind is ZoneTransitionKind.ENTERED]
    assert len(entered) == 1
    assert entered[0].zone_id == zone_b.id
    assert entered[0].warehouse_id == WAREHOUSE_B

    assert len(engine.current_occupants(zone_a.id)) == 1
    assert len(engine.current_occupants(zone_b.id)) == 1


def test_zones_filters_by_warehouse() -> None:
    zone_a = _square_zone(warehouse_id=WAREHOUSE_A)
    zone_b = _square_zone(warehouse_id=WAREHOUSE_B, camera_id=OTHER_CAMERA_ID)
    engine = PolygonZoneEngine([zone_a, zone_b])

    assert engine.zones(WAREHOUSE_A) == [zone_a]
    assert engine.zones(WAREHOUSE_B) == [zone_b]
    assert {z.id for z in engine.zones()} == {zone_a.id, zone_b.id}


def test_camera_with_no_configured_zones_produces_no_transitions() -> None:
    zone = _square_zone(camera_id=CAMERA_ID)
    engine = PolygonZoneEngine([zone])

    transitions = engine.update(T0, [_detection(camera_id=OTHER_CAMERA_ID)])

    assert transitions == []
