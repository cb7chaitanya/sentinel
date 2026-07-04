from fastapi import APIRouter

from memory.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Camera/event CRUD and query endpoints are registered here once implemented.
