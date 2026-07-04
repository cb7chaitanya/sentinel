import uuid

from memory.domain.alert import AlertCreate, AlertSeverity, AlertStatus
from memory.infra.repositories import SqlAlchemyAlertRepository

WAREHOUSE_ID = uuid.uuid4()


def _alert(
    *, warehouse_id: uuid.UUID = WAREHOUSE_ID, severity: AlertSeverity = AlertSeverity.HIGH
) -> AlertCreate:
    return AlertCreate(
        warehouse_id=warehouse_id, severity=severity, summary="Forklift proximity alert"
    )


async def test_create_defaults_to_open_status(session) -> None:
    repo = SqlAlchemyAlertRepository(session)

    alert = await repo.create(_alert())

    assert alert.status is AlertStatus.OPEN
    assert alert.severity is AlertSeverity.HIGH
    assert alert.resolved_at is None


async def test_get_returns_none_for_unknown_id(session) -> None:
    repo = SqlAlchemyAlertRepository(session)

    assert await repo.get(uuid.uuid4()) is None


async def test_list_active_excludes_resolved_alerts(session) -> None:
    repo = SqlAlchemyAlertRepository(session)
    open_alert = await repo.create(_alert())
    resolved_alert = await repo.create(_alert())
    await repo.update_status(resolved_alert.id, AlertStatus.RESOLVED)

    active = await repo.list_active(WAREHOUSE_ID)

    assert [a.id for a in active] == [open_alert.id]


async def test_list_active_includes_acknowledged_alerts(session) -> None:
    repo = SqlAlchemyAlertRepository(session)
    alert = await repo.create(_alert())
    await repo.update_status(alert.id, AlertStatus.ACKNOWLEDGED)

    active = await repo.list_active(WAREHOUSE_ID)

    assert len(active) == 1
    assert active[0].status is AlertStatus.ACKNOWLEDGED


async def test_list_active_scopes_by_warehouse(session) -> None:
    repo = SqlAlchemyAlertRepository(session)
    other_warehouse = uuid.uuid4()
    await repo.create(_alert(warehouse_id=WAREHOUSE_ID))
    await repo.create(_alert(warehouse_id=other_warehouse))

    active = await repo.list_active(WAREHOUSE_ID)

    assert len(active) == 1
    assert active[0].warehouse_id == WAREHOUSE_ID


async def test_update_status_returns_none_for_unknown_id(session) -> None:
    repo = SqlAlchemyAlertRepository(session)

    assert await repo.update_status(uuid.uuid4(), AlertStatus.RESOLVED) is None
