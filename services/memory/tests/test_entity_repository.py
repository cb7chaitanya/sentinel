import uuid
from datetime import UTC, datetime, timedelta

from memory.domain.entity import EntityObservation, EntityRead, EntityType, classify_entity_type
from memory.infra.repositories import SqlAlchemyEntityRepository
from sentinel_common.schemas.detection import BoundingBox, Velocity

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _observation(
    *,
    track_id: int = 1,
    label: str = "person",
    observed_at: datetime = T0,
    x_min: float = 0.0,
    velocity: Velocity | None = None,
) -> EntityObservation:
    return EntityObservation(
        warehouse_id=WAREHOUSE_ID,
        camera_id=CAMERA_ID,
        track_id=track_id,
        label=label,
        bounding_box=BoundingBox(x_min=x_min, y_min=0, x_max=x_min + 10, y_max=10),
        velocity=velocity,
        observed_at=observed_at,
    )


def test_classify_entity_type_uses_default_mapping() -> None:
    assert classify_entity_type("person") is EntityType.WORKER
    assert classify_entity_type("forklift") is EntityType.FORKLIFT
    assert classify_entity_type("pallet") is EntityType.PALLET
    assert classify_entity_type("box") is EntityType.BOX
    assert classify_entity_type("bicycle") is EntityType.OTHER


def test_classify_entity_type_is_case_insensitive() -> None:
    assert classify_entity_type("PERSON") is EntityType.WORKER


def test_classify_entity_type_accepts_a_custom_mapping() -> None:
    mapping = {"crate": EntityType.BOX}
    assert classify_entity_type("crate", mapping) is EntityType.BOX
    assert classify_entity_type("person", mapping) is EntityType.OTHER


async def test_record_observation_creates_a_new_entity(session) -> None:
    repo = SqlAlchemyEntityRepository(session)

    entity = await repo.record_observation(_observation())

    assert entity.warehouse_id == WAREHOUSE_ID
    assert entity.camera_id == CAMERA_ID
    assert entity.track_id == 1
    assert entity.entity_type is EntityType.WORKER
    assert entity.label == "person"
    assert entity.first_seen_at == T0
    assert entity.last_seen_at == T0
    assert entity.velocity is None


async def test_record_observation_upserts_the_same_track(session) -> None:
    repo = SqlAlchemyEntityRepository(session)

    first = await repo.record_observation(_observation(observed_at=T0, x_min=0))
    second = await repo.record_observation(
        _observation(
            observed_at=T0 + timedelta(seconds=1), x_min=5, velocity=Velocity(vx=5.0, vy=0.0)
        )
    )

    assert second.id == first.id  # same row, not a duplicate
    assert second.first_seen_at == T0  # unchanged
    assert second.last_seen_at == T0 + timedelta(seconds=1)
    assert second.bounding_box.x_min == 5
    assert second.velocity == Velocity(vx=5.0, vy=0.0)


async def test_get_returns_none_for_unknown_id(session) -> None:
    repo = SqlAlchemyEntityRepository(session)

    assert await repo.get(uuid.uuid4()) is None


async def test_get_by_track_finds_the_right_entity(session) -> None:
    repo = SqlAlchemyEntityRepository(session)
    created = await repo.record_observation(_observation(track_id=7))

    found = await repo.get_by_track(CAMERA_ID, 7)

    assert found is not None
    assert found.id == created.id


async def test_get_by_track_returns_none_when_no_match(session) -> None:
    repo = SqlAlchemyEntityRepository(session)

    assert await repo.get_by_track(CAMERA_ID, 999) is None


async def test_list_current_excludes_stale_entities(session) -> None:
    repo = SqlAlchemyEntityRepository(session)
    await repo.record_observation(_observation(track_id=1, observed_at=T0))
    await repo.record_observation(
        _observation(track_id=2, observed_at=T0 + timedelta(seconds=25))
    )

    current = await repo.list_current(
        WAREHOUSE_ID, as_of=T0 + timedelta(seconds=30), staleness_threshold_seconds=10.0
    )

    track_ids = {e.track_id for e in current}
    assert track_ids == {2}


async def test_list_current_filters_by_entity_type(session) -> None:
    repo = SqlAlchemyEntityRepository(session)
    await repo.record_observation(_observation(track_id=1, label="person", observed_at=T0))
    await repo.record_observation(_observation(track_id=2, label="forklift", observed_at=T0))

    workers = await repo.list_current(
        WAREHOUSE_ID,
        as_of=T0,
        staleness_threshold_seconds=60.0,
        entity_type=EntityType.WORKER,
    )

    assert [e.track_id for e in workers] == [1]


async def test_list_current_is_ordered_deterministically(session) -> None:
    repo = SqlAlchemyEntityRepository(session)
    for track_id, offset in [(1, 0), (2, 5), (3, 2)]:
        await repo.record_observation(
            _observation(track_id=track_id, observed_at=T0 + timedelta(seconds=offset))
        )

    current = await repo.list_current(
        WAREHOUSE_ID, as_of=T0 + timedelta(seconds=10), staleness_threshold_seconds=60.0
    )

    # Newest last_seen_at first.
    assert [e.track_id for e in current] == [2, 3, 1]


async def test_list_current_scopes_by_warehouse(session) -> None:
    repo = SqlAlchemyEntityRepository(session)
    other_warehouse = uuid.uuid4()
    await repo.record_observation(_observation(track_id=1, observed_at=T0))
    await repo.record_observation(
        EntityObservation(
            warehouse_id=other_warehouse,
            camera_id=uuid.uuid4(),
            track_id=1,
            label="person",
            bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
            observed_at=T0,
        )
    )

    current = await repo.list_current(
        WAREHOUSE_ID, as_of=T0, staleness_threshold_seconds=60.0
    )

    assert len(current) == 1
    assert current[0].warehouse_id == WAREHOUSE_ID


def test_is_active_reflects_staleness_threshold() -> None:
    entity = EntityRead(
        id=uuid.uuid4(),
        created_at=T0,
        updated_at=T0,
        warehouse_id=WAREHOUSE_ID,
        camera_id=CAMERA_ID,
        track_id=1,
        entity_type=EntityType.WORKER,
        label="person",
        bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
        first_seen_at=T0,
        last_seen_at=T0,
    )

    soon = T0 + timedelta(seconds=5)
    later = T0 + timedelta(seconds=15)
    assert entity.is_active(as_of=soon, staleness_threshold_seconds=10) is True
    assert entity.is_active(as_of=later, staleness_threshold_seconds=10) is False
