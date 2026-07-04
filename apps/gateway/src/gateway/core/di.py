"""Composition root for the gateway's dependencies.

Downstream service clients are constructed here and wired into routers via
FastAPI's `Depends()`. No business/orchestration logic lives in this file.

The HTTP client is a process-wide singleton, not request-scoped: the
warehouse-state poll loop (`WarehouseStateBroadcaster`) outlives any single
request, and reusing one pooled client for it plus every proxy route is
strictly better than opening a new connection pool per request.
"""

from typing import Annotated

import httpx
from fastapi import Depends
from sentinel_common.di import singleton

from gateway.core.config import Settings, get_settings
from gateway.core.warehouse_state_broadcaster import WarehouseStateBroadcaster

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


@singleton
def get_warehouse_state_broadcaster() -> WarehouseStateBroadcaster:
    settings = get_settings()
    return WarehouseStateBroadcaster(
        http_client=get_http_client(),
        memory_service_url=settings.memory_service_url,
        poll_interval_seconds=settings.warehouse_state_poll_interval_seconds,
    )


WarehouseStateBroadcasterDep = Annotated[
    WarehouseStateBroadcaster, Depends(get_warehouse_state_broadcaster)
]
