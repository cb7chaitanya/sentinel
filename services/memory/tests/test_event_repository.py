import uuid
from datetime import UTC, datetime, timedelta

from memory.infra.repositories import SqlAlchemyEventRepository
from sentinel_common.schemas.event import EventCreate, EventType

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _event(
    *,
    occurred_at: datetime = T0,
    event_type: EventType = EventType.OBJECT_MOVED,
    track_id: int | None = 1,
    warehouse_id: uuid.UUID | None = WAREHOUSE_ID,
    camera_id: uuid.UUID = CAMERA_ID,
) -> EventCreate:
    return EventCreate(
        camera_id=camera_id,
        event_type=event_type,
        occurred_at=occurred_at,
        summary="Pallet moved",
        warehouse_id=warehouse_id,
        track_id=track_id,
    )


async def test_create_and_get_round_trip(session) -> None:
    repo = SqlAlchemyEventRepository(session)

    created = await repo.create(_event())
    fetched = await repo.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.event_type is EventType.OBJECT_MOVED
    assert fetched.warehouse_id == WAREHOUSE_ID
    assert fetched.summary == "Pallet moved"


async def test_get_returns_none_for_unknown_id(session) -> None:
    repo = SqlAlchemyEventRepository(session)

    assert await repo.get(uuid.uuid4()) is None


async def test_list_for_camera_is_chronological(session) -> None:
    repo = SqlAlchemyEventRepository(session)
    await repo.create(_event(occurred_at=T0 + timedelta(seconds=5)))
    await repo.create(_event(occurred_at=T0))

    events = await repo.list_for_camera(CAMERA_ID)

    assert [e.occurred_at for e in events] == [T0, T0 + timedelta(seconds=5)]


async def test_list_for_track_filters_by_camera_and_track(session) -> None:
    repo = SqlAlchemyEventRepository(session)
    other_camera = uuid.uuid4()
    await repo.create(_event(track_id=1, camera_id=CAMERA_ID))
    await repo.create(_event(track_id=2, camera_id=CAMERA_ID))
    await repo.create(_event(track_id=1, camera_id=other_camera))

    events = await repo.list_for_track(CAMERA_ID, 1)

    assert len(events) == 1
    assert events[0].track_id == 1
    assert events[0].camera_id == CAMERA_ID


async def test_list_recent_orders_newest_first_and_scopes_by_warehouse(session) -> None:
    repo = SqlAlchemyEventRepository(session)
    other_warehouse = uuid.uuid4()
    await repo.create(_event(occurred_at=T0, warehouse_id=WAREHOUSE_ID))
    await repo.create(_event(occurred_at=T0 + timedelta(seconds=10), warehouse_id=WAREHOUSE_ID))
    await repo.create(_event(occurred_at=T0 + timedelta(seconds=20), warehouse_id=other_warehouse))

    recent = await repo.list_recent(WAREHOUSE_ID, limit=10)

    assert [e.occurred_at for e in recent] == [T0 + timedelta(seconds=10), T0]


async def test_list_recent_respects_limit(session) -> None:
    repo = SqlAlchemyEventRepository(session)
    for i in range(5):
        await repo.create(_event(occurred_at=T0 + timedelta(seconds=i)))

    recent = await repo.list_recent(WAREHOUSE_ID, limit=2)

    assert len(recent) == 2
    assert recent[0].occurred_at == T0 + timedelta(seconds=4)
    assert recent[1].occurred_at == T0 + timedelta(seconds=3)


async def test_list_recent_paginates_with_before_cursor(session) -> None:
    repo = SqlAlchemyEventRepository(session)
    for i in range(5):
        await repo.create(_event(occurred_at=T0 + timedelta(seconds=i)))

    first_page = await repo.list_recent(WAREHOUSE_ID, limit=2)
    second_page = await repo.list_recent(
        WAREHOUSE_ID, limit=2, before=first_page[-1].occurred_at
    )

    assert [e.occurred_at for e in first_page] == [
        T0 + timedelta(seconds=4),
        T0 + timedelta(seconds=3),
    ]
    assert [e.occurred_at for e in second_page] == [
        T0 + timedelta(seconds=2),
        T0 + timedelta(seconds=1),
    ]
