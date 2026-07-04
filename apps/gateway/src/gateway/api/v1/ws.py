"""WebSocket relay for live warehouse state -- see `core.warehouse_state_broadcaster`."""

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway.core.di import WarehouseStateBroadcasterDep

router = APIRouter()


@router.websocket("/ws/warehouse/{warehouse_id}")
async def warehouse_state_ws(
    websocket: WebSocket, warehouse_id: uuid.UUID, broadcaster: WarehouseStateBroadcasterDep
) -> None:
    await websocket.accept()
    try:
        async for payload in broadcaster.subscribe(warehouse_id):
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
