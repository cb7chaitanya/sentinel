import uuid
from datetime import UTC, datetime, timedelta

import pytest
from memory.core.warehouse_memory_service import EntityNotFoundError, WarehouseMemoryService
from memory.domain.alert import AlertCreate, AlertSeverity
from memory.domain.entity import EntityObservation
from memory.infra.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyEntityRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyZoneOccupancyRepository,
)
from sentinel_common.schemas.detection import BoundingBox
from sentinel_common.schemas.event import EventCreate, EventType
from sentinel_common.schemas.zone import ZoneTransition, ZoneTransitionKind

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _service(session) -> WarehouseMemoryService:
    return WarehouseMemoryService(
        SqlAlchemyEntityRepository(session),
        SqlAlchemyZoneOccupancyRepository(session),
        SqlAlchemyEventRepository(session),
        SqlAlchemyAlertRepository(session),
        entity_staleness_seconds=30.0,
        default_recent_events_limit=50,
    )


def _observation(
    *, track_id: int = 1, label: str = "forklift", observed_at: datetime = T0
) -> EntityObservation:
    return EntityObservation(
        warehouse_id=WAREHOUSE_ID,
        camera_id=CAMERA_ID,
        track_id=track_id,
        label=label,
        bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
        observed_at=observed_at,
    )


async def test_record_zone_transition_requires_a_known_entity(session) -> None:
    service = _service(session)
    transition = ZoneTransition(
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        camera_id=CAMERA_ID,
        track_id=1,
        kind=ZoneTransitionKind.ENTERED,
        occurred_at=T0,
    )

    with pytest.raises(EntityNotFoundError):
        await service.record_zone_transition(transition)


async def test_record_zone_transition_enter_then_exit(session) -> None:
    service = _service(session)
    await service.record_observation(_observation())

    entered = await service.record_zone_transition(
        ZoneTransition(
            warehouse_id=WAREHOUSE_ID,
            zone_id=ZONE_ID,
            zone_name="Loading Dock",
            camera_id=CAMERA_ID,
            track_id=1,
            kind=ZoneTransitionKind.ENTERED,
            occurred_at=T0,
        )
    )
    exited = await service.record_zone_transition(
        ZoneTransition(
            warehouse_id=WAREHOUSE_ID,
            zone_id=ZONE_ID,
            zone_name="Loading Dock",
            camera_id=CAMERA_ID,
            track_id=1,
            kind=ZoneTransitionKind.EXITED,
            occurred_at=T0 + timedelta(seconds=30),
            dwell_time_seconds=30.0,
        )
    )

    assert entered is not None
    assert exited is not None
    assert exited.exited_at == T0 + timedelta(seconds=30)


async def test_get_current_state_aggregates_everything(session) -> None:
    service = _service(session)
    entity = await service.record_observation(_observation())
    await service.record_zone_transition(
        ZoneTransition(
            warehouse_id=WAREHOUSE_ID,
            zone_id=ZONE_ID,
            zone_name="Loading Dock",
            camera_id=CAMERA_ID,
            track_id=1,
            kind=ZoneTransitionKind.ENTERED,
            occurred_at=T0,
        )
    )
    await service.record_event(
        EventCreate(
            camera_id=CAMERA_ID,
            event_type=EventType.ZONE_ENTERED,
            occurred_at=T0,
            summary="Forklift entered Loading Dock",
            warehouse_id=WAREHOUSE_ID,
            track_id=1,
        )
    )
    await service.record_alert(
        AlertCreate(warehouse_id=WAREHOUSE_ID, severity=AlertSeverity.MEDIUM, summary="test alert")
    )

    state = await service.get_current_state(WAREHOUSE_ID, as_of=T0 + timedelta(seconds=5))

    assert state.warehouse_id == WAREHOUSE_ID
    assert len(state.entities) == 1
    assert state.entities[0].id == entity.id
    assert len(state.zone_occupancy) == 1
    assert state.zone_occupancy[0].zone_id == ZONE_ID
    assert len(state.recent_events) == 1
    assert len(state.active_alerts) == 1


async def test_get_current_state_excludes_stale_entities(session) -> None:
    service = _service(session)
    await service.record_observation(_observation(track_id=1, observed_at=T0))
    await service.record_observation(
        _observation(track_id=2, observed_at=T0 + timedelta(seconds=40))
    )

    state = await service.get_current_state(
        WAREHOUSE_ID, as_of=T0 + timedelta(seconds=40)
    )

    assert [e.track_id for e in state.entities] == [2]


async def test_get_recent_events_delegates_to_the_event_repository(session) -> None:
    service = _service(session)
    await service.record_event(
        EventCreate(
            camera_id=CAMERA_ID,
            event_type=EventType.OBJECT_MOVED,
            occurred_at=T0,
            summary="Pallet moved",
            warehouse_id=WAREHOUSE_ID,
        )
    )

    events = await service.get_recent_events(WAREHOUSE_ID, limit=10)

    assert len(events) == 1
    assert events[0].summary == "Pallet moved"


async def test_get_entity_history_returns_none_for_unknown_entity(session) -> None:
    service = _service(session)

    assert await service.get_entity_history(uuid.uuid4()) is None


async def test_get_entity_history_combines_zone_occupancy_and_events(session) -> None:
    service = _service(session)
    entity = await service.record_observation(_observation())
    await service.record_zone_transition(
        ZoneTransition(
            warehouse_id=WAREHOUSE_ID,
            zone_id=ZONE_ID,
            zone_name="Loading Dock",
            camera_id=CAMERA_ID,
            track_id=1,
            kind=ZoneTransitionKind.ENTERED,
            occurred_at=T0,
        )
    )
    await service.record_event(
        EventCreate(
            camera_id=CAMERA_ID,
            event_type=EventType.ZONE_ENTERED,
            occurred_at=T0,
            summary="Forklift entered Loading Dock",
            warehouse_id=WAREHOUSE_ID,
            track_id=1,
        )
    )

    history = await service.get_entity_history(entity.id)

    assert history is not None
    assert history.entity.id == entity.id
    assert len(history.zone_occupancy) == 1
    assert len(history.events) == 1


async def test_multiple_warehouses_do_not_leak_into_each_others_state(session) -> None:
    service = _service(session)
    other_warehouse = uuid.uuid4()
    other_camera = uuid.uuid4()

    await service.record_observation(_observation(track_id=1))
    await service.record_observation(
        EntityObservation(
            warehouse_id=other_warehouse,
            camera_id=other_camera,
            track_id=1,
            label="pallet",
            bounding_box=BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10),
            observed_at=T0,
        )
    )

    state = await service.get_current_state(WAREHOUSE_ID, as_of=T0)

    assert len(state.entities) == 1
    assert state.entities[0].warehouse_id == WAREHOUSE_ID
