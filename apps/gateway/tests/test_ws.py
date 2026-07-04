import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient
from gateway.core.di import get_warehouse_state_broadcaster
from gateway.main import app

WAREHOUSE_ID = uuid.uuid4()


class FakeBroadcaster:
    async def subscribe(self, warehouse_id: uuid.UUID) -> AsyncIterator[dict[str, Any]]:
        yield {"warehouse_id": str(warehouse_id), "seq": 1}
        yield {"warehouse_id": str(warehouse_id), "seq": 2}


def test_warehouse_state_ws_streams_polled_payloads() -> None:
    app.dependency_overrides[get_warehouse_state_broadcaster] = lambda: FakeBroadcaster()
    try:
        with (
            TestClient(app) as client,
            client.websocket_connect(f"/api/v1/ws/warehouse/{WAREHOUSE_ID}") as websocket,
        ):
            first = websocket.receive_json()
            second = websocket.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert first == {"warehouse_id": str(WAREHOUSE_ID), "seq": 1}
    assert second == {"warehouse_id": str(WAREHOUSE_ID), "seq": 2}
