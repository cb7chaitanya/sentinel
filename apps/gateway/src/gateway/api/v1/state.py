"""Proxies the memory service's warehouse-state read for the dashboard.

Used both for the dashboard's initial load (before its WebSocket connects)
and as the one endpoint the warehouse-state poll loop itself calls -- see
`core/warehouse_state_broadcaster.py`.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from gateway.core.di import HttpClientDep, SettingsDep

router = APIRouter()


@router.get("/state/{warehouse_id}")
async def get_warehouse_state(
    warehouse_id: uuid.UUID,
    client: HttpClientDep,
    settings: SettingsDep,
    as_of: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    params = {"as_of": as_of.isoformat()} if as_of is not None else None
    response = await client.get(
        f"{settings.memory_service_url}/api/v1/state/{warehouse_id}", params=params
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
