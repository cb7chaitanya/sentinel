from fastapi import APIRouter

from memory.api.v1 import alerts, entities, events, health, state, zones

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(state.router, tags=["state"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(entities.router, tags=["entities"])
api_router.include_router(zones.router, tags=["zones"])
api_router.include_router(alerts.router, tags=["alerts"])

# Camera CRUD endpoints are registered here once implemented.
