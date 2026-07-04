import uuid
from datetime import UTC, datetime, timedelta

from memory.domain.entity import EntityObservation
from memory.infra.repositories import SqlAlchemyEntityRepository, SqlAlchemyZoneOccupancyRepository
from sentinel_common.schemas.detection import BoundingBox

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


async def _make_entity(session, *, track_id: int = 1) -> uuid.UUID:
    repo = SqlAlchemyEntityRepository(session)
    entity = await repo.record_observation(
        EntityObservation(
            warehouse_id=WAREHOUSE_ID,
            camera_id=CAMERA_ID,
            track_id=track_id,
            label="person",
            bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
            observed_at=T0,
        )
    )
    return entity.id


async def test_record_entered_creates_an_open_interval(session) -> None:
    entity_id = await _make_entity(session)
    repo = SqlAlchemyZoneOccupancyRepository(session)

    occupancy = await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )

    assert occupancy.entity_id == entity_id
    assert occupancy.zone_name == "Loading Dock"
    assert occupancy.entered_at == T0
    assert occupancy.exited_at is None
    assert occupancy.dwell_time_seconds(as_of=T0 + timedelta(seconds=5)) == 5.0


async def test_record_exited_closes_the_open_interval(session) -> None:
    entity_id = await _make_entity(session)
    repo = SqlAlchemyZoneOccupancyRepository(session)
    await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )

    closed = await repo.record_exited(
        entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0 + timedelta(seconds=10)
    )

    assert closed is not None
    assert closed.exited_at == T0 + timedelta(seconds=10)
    assert closed.dwell_time_seconds() == 10.0


async def test_record_exited_returns_none_without_a_matching_open_interval(session) -> None:
    entity_id = await _make_entity(session)
    repo = SqlAlchemyZoneOccupancyRepository(session)

    result = await repo.record_exited(entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0)

    assert result is None


async def test_list_current_only_returns_open_intervals(session) -> None:
    entity_id = await _make_entity(session, track_id=1)
    other_entity_id = await _make_entity(session, track_id=2)
    repo = SqlAlchemyZoneOccupancyRepository(session)

    await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )
    still_open = await repo.record_entered(
        entity_id=other_entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )
    await repo.record_exited(
        entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0 + timedelta(seconds=1)
    )

    current = await repo.list_current(WAREHOUSE_ID)

    assert [o.id for o in current] == [still_open.id]


async def test_list_for_entity_returns_full_history_oldest_first(session) -> None:
    entity_id = await _make_entity(session)
    repo = SqlAlchemyZoneOccupancyRepository(session)
    zone_2 = uuid.uuid4()

    await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )
    await repo.record_exited(
        entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0 + timedelta(seconds=5)
    )
    await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=zone_2,
        zone_name="Staging Area",
        entered_at=T0 + timedelta(seconds=10),
    )

    history = await repo.list_for_entity(entity_id)

    assert len(history) == 2
    assert history[0].zone_id == ZONE_ID
    assert history[0].exited_at is not None
    assert history[1].zone_id == zone_2
    assert history[1].exited_at is None


async def test_re_entering_the_same_zone_after_exiting_creates_a_new_interval(session) -> None:
    entity_id = await _make_entity(session)
    repo = SqlAlchemyZoneOccupancyRepository(session)

    first = await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0,
    )
    await repo.record_exited(
        entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0 + timedelta(seconds=5)
    )
    second = await repo.record_entered(
        entity_id=entity_id,
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        entered_at=T0 + timedelta(seconds=20),
    )

    assert second.id != first.id
    # Closing again should only affect the newer, still-open interval.
    closed = await repo.record_exited(
        entity_id=entity_id, zone_id=ZONE_ID, exited_at=T0 + timedelta(seconds=25)
    )
    assert closed is not None
    assert closed.id == second.id
