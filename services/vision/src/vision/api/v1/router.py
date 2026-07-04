from fastapi import APIRouter

from vision.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Detection endpoints are registered here once implemented.
