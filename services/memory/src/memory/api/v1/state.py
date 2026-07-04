import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from memory.core.di import WarehouseMemoryServiceDep
from memory.domain.state import WarehouseState

router = APIRouter()


@router.get("/state/{warehouse_id}", response_model=WarehouseState)
async def get_current_state(
    warehouse_id: uuid.UUID,
    memory: WarehouseMemoryServiceDep,
    as_of: Annotated[datetime | None, Query()] = None,
) -> WarehouseState:
    return await memory.get_current_state(warehouse_id, as_of=as_of)
