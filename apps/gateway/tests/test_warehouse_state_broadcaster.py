import asyncio
import uuid

import httpx
from gateway.core.warehouse_state_broadcaster import WarehouseStateBroadcaster

WAREHOUSE_ID = uuid.uuid4()


def _broadcaster(handler, *, poll_interval_seconds: float = 0.02) -> WarehouseStateBroadcaster:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WarehouseStateBroadcaster(
        http_client=client,
        memory_service_url="http://memory:8004",
        poll_interval_seconds=poll_interval_seconds,
    )


async def test_subscriber_receives_polled_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/state/{WAREHOUSE_ID}"
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID), "entities": []})

    broadcaster = _broadcaster(handler)
    subscription = broadcaster.subscribe(WAREHOUSE_ID)

    payload = await asyncio.wait_for(subscription.__anext__(), timeout=1.0)

    assert payload["warehouse_id"] == str(WAREHOUSE_ID)
    await subscription.aclose()


async def test_two_subscribers_to_the_same_warehouse_share_one_poll_task() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID)})

    broadcaster = _broadcaster(handler)
    first = broadcaster.subscribe(WAREHOUSE_ID)
    second = broadcaster.subscribe(WAREHOUSE_ID)

    await asyncio.wait_for(first.__anext__(), timeout=1.0)
    await asyncio.wait_for(second.__anext__(), timeout=1.0)

    assert len(broadcaster._tasks) == 1

    await first.aclose()
    await second.aclose()


async def test_poll_task_stops_once_the_last_subscriber_disconnects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID)})

    broadcaster = _broadcaster(handler)
    subscription = broadcaster.subscribe(WAREHOUSE_ID)
    await asyncio.wait_for(subscription.__anext__(), timeout=1.0)

    assert WAREHOUSE_ID in broadcaster._tasks

    await subscription.aclose()

    assert WAREHOUSE_ID not in broadcaster._tasks
    assert WAREHOUSE_ID not in broadcaster._subscribers


async def test_a_failed_poll_does_not_crash_the_loop() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500)
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID), "attempt": attempts})

    broadcaster = _broadcaster(handler)
    subscription = broadcaster.subscribe(WAREHOUSE_ID)

    payload = await asyncio.wait_for(subscription.__anext__(), timeout=1.0)

    assert attempts >= 2
    assert payload["attempt"] == attempts
    await subscription.aclose()
