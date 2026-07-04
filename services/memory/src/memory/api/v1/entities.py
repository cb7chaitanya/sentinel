import uuid

from fastapi import APIRouter, HTTPException

from memory.core.di import WarehouseMemoryServiceDep
from memory.domain.entity import EntityObservation, EntityRead
from memory.domain.state import EntityHistory

router = APIRouter()


@router.post("/observations", response_model=EntityRead, status_code=201)
async def record_observation(
    observation: EntityObservation, memory: WarehouseMemoryServiceDep
) -> EntityRead:
    return await memory.record_observation(observation)


@router.get("/entities/{entity_id}/history", response_model=EntityHistory)
async def get_entity_history(
    entity_id: uuid.UUID, memory: WarehouseMemoryServiceDep
) -> EntityHistory:
    history = await memory.get_entity_history(entity_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"no entity {entity_id}")
    return history
