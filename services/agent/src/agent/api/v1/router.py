from fastapi import APIRouter

from agent.api.v1 import copilot, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(copilot.router, tags=["copilot"])
