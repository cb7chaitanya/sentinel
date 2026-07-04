from fastapi import APIRouter

from sentinel_common.schemas.common import SentinelModel

router = APIRouter()


class HealthResponse(SentinelModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="events")
