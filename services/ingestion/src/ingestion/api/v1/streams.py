import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ingestion.core.di import FrameBroadcasterDep, StreamRegistryDep
from ingestion.core.frame_broadcaster import FrameBroadcaster
from ingestion.domain.camera import StreamHealth

router = APIRouter()

_MJPEG_BOUNDARY = "sentinelframe"


@router.get("/streams", response_model=list[StreamHealth])
async def list_streams(registry: StreamRegistryDep) -> list[StreamHealth]:
    return await registry.list_health()


@router.get("/streams/{camera_id}/health", response_model=StreamHealth)
async def get_stream_health(camera_id: uuid.UUID, registry: StreamRegistryDep) -> StreamHealth:
    health = await registry.health(camera_id)
    if health is None:
        raise HTTPException(status_code=404, detail=f"no configured stream for camera {camera_id}")
    return health


@router.get("/streams/{camera_id}/mjpeg")
async def stream_mjpeg(
    camera_id: uuid.UUID, registry: StreamRegistryDep, broadcaster: FrameBroadcasterDep
) -> StreamingResponse:
    health = await registry.health(camera_id)
    if health is None:
        raise HTTPException(status_code=404, detail=f"no configured stream for camera {camera_id}")

    return StreamingResponse(
        _mjpeg_parts(broadcaster, camera_id),
        media_type=f"multipart/x-mixed-replace; boundary={_MJPEG_BOUNDARY}",
    )


async def _mjpeg_parts(broadcaster: FrameBroadcaster, camera_id: uuid.UUID) -> AsyncIterator[bytes]:
    async for frame in broadcaster.subscribe(camera_id):
        header = (
            f"--{_MJPEG_BOUNDARY}\r\n"
            "Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(frame.data)}\r\n\r\n"
        ).encode()
        yield header + frame.data + b"\r\n"
