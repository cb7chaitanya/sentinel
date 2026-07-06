from fastapi import APIRouter
from sentinel_common.schemas.detection import FrameDetections

from events.core.di import DetectionIngestServiceDep

router = APIRouter()


@router.post("/detections", status_code=202)
async def ingest_detections(
    frame_detections: FrameDetections, ingest: DetectionIngestServiceDep
) -> None:
    await ingest.ingest(frame_detections)
