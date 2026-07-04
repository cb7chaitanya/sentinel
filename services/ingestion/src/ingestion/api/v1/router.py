from fastapi import APIRouter

from ingestion.api.v1 import health, streams

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(streams.router, tags=["streams"])
