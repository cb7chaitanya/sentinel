"""Fans out live warehouse state to WebSocket subscribers via server-side polling.

The dashboard wants push-based updates, but memory only exposes a
pull-based `GET /state/{warehouse_id}`; this bridges the two with one
background poll loop per warehouse -- started on first subscriber, stopped
once the last one disconnects -- rather than one poll loop per connected
client, so N dashboards watching the same warehouse cost one upstream
request per interval, not N.

Subscribers are handed the raw JSON payload memory returns, not a parsed
domain type: the gateway composes services, it doesn't own their wire
schemas (that's why `AgentAnalysis`/`WarehouseState`/etc. are never
imported here).
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WarehouseStatePayload = dict[str, Any]


def _put_latest(
    queue: "asyncio.Queue[WarehouseStatePayload]", payload: WarehouseStatePayload
) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        pass


class WarehouseStateBroadcaster:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        memory_service_url: str,
        poll_interval_seconds: float,
    ) -> None:
        self._http = http_client
        self._base_url = memory_service_url.rstrip("/")
        self._poll_interval_seconds = poll_interval_seconds
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue[WarehouseStatePayload]]] = {}
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def subscribe(self, warehouse_id: uuid.UUID) -> AsyncIterator[WarehouseStatePayload]:
        """Yield warehouse-state payloads for `warehouse_id` until cancelled."""
        queue: asyncio.Queue[WarehouseStatePayload] = asyncio.Queue(maxsize=1)
        subscribers = self._subscribers.setdefault(warehouse_id, set())
        subscribers.add(queue)
        if warehouse_id not in self._tasks:
            self._tasks[warehouse_id] = asyncio.create_task(
                self._poll(warehouse_id), name=f"warehouse-state-poll-{warehouse_id}"
            )
        try:
            while True:
                yield await queue.get()
        finally:
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(warehouse_id, None)
                task = self._tasks.pop(warehouse_id, None)
                if task is not None:
                    task.cancel()

    async def _poll(self, warehouse_id: uuid.UUID) -> None:
        try:
            while True:
                await self._poll_once(warehouse_id)
                await asyncio.sleep(self._poll_interval_seconds)
        except asyncio.CancelledError:
            raise

    async def _poll_once(self, warehouse_id: uuid.UUID) -> None:
        try:
            response = await self._http.get(f"{self._base_url}/api/v1/state/{warehouse_id}")
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError:
            logger.warning(
                "failed to poll warehouse state for %s", warehouse_id, exc_info=True
            )
            return

        for queue in list(self._subscribers.get(warehouse_id, ())):
            _put_latest(queue, payload)
