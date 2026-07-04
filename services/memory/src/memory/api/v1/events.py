import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sentinel_common.schemas.event import EventCreate, EventRead

from memory.core.di import WarehouseMemoryServiceDep

router = APIRouter()


@router.get("/events", response_model=list[EventRead])
async def get_recent_events(
    memory: WarehouseMemoryServiceDep,
    warehouse_id: uuid.UUID,
    limit: Annotated[int, Query(gt=0, le=500)] = 50,
    before: Annotated[datetime | None, Query()] = None,
) -> list[EventRead]:
    return await memory.get_recent_events(warehouse_id, limit=limit, before=before)


@router.post("/events", response_model=EventRead, status_code=201)
async def record_event(event: EventCreate, memory: WarehouseMemoryServiceDep) -> EventRead:
    return await memory.record_event(event)
