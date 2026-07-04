from fastapi import APIRouter, HTTPException
from sentinel_common.schemas.zone import ZoneTransition

from memory.core.di import WarehouseMemoryServiceDep
from memory.core.warehouse_memory_service import EntityNotFoundError
from memory.domain.zone_occupancy import ZoneOccupancyRead

router = APIRouter()


@router.post("/zone-transitions", response_model=ZoneOccupancyRead | None)
async def record_zone_transition(
    transition: ZoneTransition, memory: WarehouseMemoryServiceDep
) -> ZoneOccupancyRead | None:
    try:
        occupancy = await memory.record_zone_transition(transition)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if occupancy is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"no open zone_occupancy interval for camera={transition.camera_id} "
                f"track_id={transition.track_id} zone_id={transition.zone_id}"
            ),
        )
    return occupancy
