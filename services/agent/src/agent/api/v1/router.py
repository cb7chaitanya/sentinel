from fastapi import APIRouter

from agent.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Agent chat/query endpoints are registered here once implemented.
