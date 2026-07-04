from fastapi import APIRouter

from gateway.api.v1 import cameras, copilot, health, state, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(state.router, tags=["state"])
api_router.include_router(copilot.router, tags=["copilot"])
api_router.include_router(cameras.router, tags=["cameras"])
api_router.include_router(ws.router, tags=["ws"])
