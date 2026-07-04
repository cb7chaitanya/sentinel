import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from memory.core.di import AlertRepositoryDep, WarehouseMemoryServiceDep
from memory.domain.alert import AlertCreate, AlertRead, AlertStatus

router = APIRouter()


@router.post("/alerts", response_model=AlertRead, status_code=201)
async def record_alert(alert: AlertCreate, memory: WarehouseMemoryServiceDep) -> AlertRead:
    return await memory.record_alert(alert)


@router.get("/alerts/{alert_id}", response_model=AlertRead)
async def get_alert(alert_id: uuid.UUID, alerts: AlertRepositoryDep) -> AlertRead:
    alert = await alerts.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"no alert {alert_id}")
    return alert


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(alert_id: uuid.UUID, alerts: AlertRepositoryDep) -> AlertRead:
    updated = await alerts.update_status(alert_id, AlertStatus.ACKNOWLEDGED)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"no alert {alert_id}")
    return updated


@router.post("/alerts/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(alert_id: uuid.UUID, alerts: AlertRepositoryDep) -> AlertRead:
    updated = await alerts.update_status(
        alert_id, AlertStatus.RESOLVED, resolved_at=datetime.now(UTC)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"no alert {alert_id}")
    return updated
