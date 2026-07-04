from fastapi import APIRouter

from events.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Event extraction/query endpoints are registered here once implemented.
