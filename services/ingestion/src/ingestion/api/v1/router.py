from fastapi import APIRouter

from ingestion.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Camera/stream management endpoints are registered here once implemented.
