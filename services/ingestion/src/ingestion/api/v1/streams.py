import uuid

from fastapi import APIRouter, HTTPException

from ingestion.core.di import StreamRegistryDep
from ingestion.domain.camera import StreamHealth

router = APIRouter()


@router.get("/streams", response_model=list[StreamHealth])
async def list_streams(registry: StreamRegistryDep) -> list[StreamHealth]:
    return await registry.list_health()


@router.get("/streams/{camera_id}/health", response_model=StreamHealth)
async def get_stream_health(camera_id: uuid.UUID, registry: StreamRegistryDep) -> StreamHealth:
    health = await registry.health(camera_id)
    if health is None:
        raise HTTPException(status_code=404, detail=f"no configured stream for camera {camera_id}")
    return health
