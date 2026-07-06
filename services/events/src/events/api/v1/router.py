from fastapi import APIRouter

from events.api.v1 import detections, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(detections.router, tags=["detections"])
