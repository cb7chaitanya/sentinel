"""Thin async HTTP client for pushing derived state into the memory service.

The events and memory services are separate deployables, so this is a
plain HTTP boundary (`httpx`), not an in-process import -- mirrors the
agent service's own `MemoryClient` for the read side. Each method maps
one domain write (`EntityObservation`/`ZoneTransition`/`EventCreate`) onto
the matching memory endpoint and raises on failure; callers decide how to
handle a single write failing (see `core/ingest_service.py`).
"""

import httpx
from sentinel_common.schemas.entity import EntityObservation
from sentinel_common.schemas.event import EventCreate
from sentinel_common.schemas.zone import ZoneTransition


class MemoryClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    async def record_observation(self, observation: EntityObservation) -> None:
        response = await self._http.post(
            f"{self._base_url}/api/v1/observations",
            content=observation.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    async def record_zone_transition(self, transition: ZoneTransition) -> None:
        response = await self._http.post(
            f"{self._base_url}/api/v1/zone-transitions",
            content=transition.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    async def record_event(self, event: EventCreate) -> None:
        response = await self._http.post(
            f"{self._base_url}/api/v1/events",
            content=event.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
