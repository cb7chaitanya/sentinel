from fastapi import APIRouter

from gateway.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Additional composed routers (cameras, events, agent-chat, ...) are
# registered here as the corresponding downstream services come online.
