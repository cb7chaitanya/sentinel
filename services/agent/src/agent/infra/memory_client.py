"""Thin async HTTP client for the memory service's read API.

The agent and memory services are separate deployables, so this is a
plain HTTP boundary (`httpx`), not an in-process import -- `WarehouseState`/
`EntityHistory`/etc. never leave memory's process as Python objects, only
as JSON, which this module maps into the agent's own local evidence
shapes (`domain.evidence`, `domain.context.EntitySnapshot`).

`get_current_snapshot` deliberately does not reuse `/state/{warehouse_id}`
for events: that endpoint bounds `recent_events` to the memory service's
own default window, which is tuned for the reasoning agent's "what's
happening right now" use case, not "what happened in this zone" -- a
question that may need to look further back. It calls `/events` directly
with a wider limit instead.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sentinel_common.schemas.event import EventRead

from agent.domain.context import EntitySnapshot, ZoneMembership
from agent.domain.evidence import AlertRecord, RetrievedEvidence

_EVENTS_WINDOW = 200


class MemoryClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    async def get_current_snapshot(self, warehouse_id: uuid.UUID) -> RetrievedEvidence:
        state_response = await self._http.get(f"{self._base_url}/api/v1/state/{warehouse_id}")
        state_response.raise_for_status()
        state = state_response.json()

        events_response = await self._http.get(
            f"{self._base_url}/api/v1/events",
            params={"warehouse_id": str(warehouse_id), "limit": _EVENTS_WINDOW},
        )
        events_response.raise_for_status()

        return RetrievedEvidence(
            entities=[
                _entity_snapshot(entity, state["zone_occupancy"]) for entity in state["entities"]
            ],
            events=[EventRead.model_validate(event) for event in events_response.json()],
            alerts=[_alert_record(alert) for alert in state["active_alerts"]],
        )

    async def get_entity_history(
        self, entity_id: uuid.UUID
    ) -> tuple[EntitySnapshot, list[EventRead]] | None:
        response = await self._http.get(f"{self._base_url}/api/v1/entities/{entity_id}/history")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

        entity = _entity_snapshot(data["entity"], data["zone_occupancy"])
        events = [EventRead.model_validate(event) for event in data["events"]]
        return entity, events

    async def get_alert(self, alert_id: uuid.UUID) -> AlertRecord | None:
        response = await self._http.get(f"{self._base_url}/api/v1/alerts/{alert_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _alert_record(response.json())

    async def get_event(self, event_id: uuid.UUID) -> EventRead | None:
        response = await self._http.get(f"{self._base_url}/api/v1/events/{event_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return EventRead.model_validate(response.json())


def _entity_snapshot(
    entity: dict[str, Any], zone_occupancy: list[dict[str, Any]]
) -> EntitySnapshot:
    current_zones = [
        ZoneMembership(
            zone_name=zone["zone_name"],
            dwell_time_seconds=_dwell_seconds(zone["entered_at"]),
        )
        for zone in zone_occupancy
        if zone["entity_id"] == entity["id"] and zone["exited_at"] is None
    ]
    return EntitySnapshot(
        entity_id=entity["id"],
        entity_type=entity["entity_type"],
        label=entity["label"],
        camera_id=entity["camera_id"],
        last_seen_at=entity["last_seen_at"],
        current_zones=current_zones,
    )


def _dwell_seconds(entered_at: str) -> float:
    return max((datetime.now(UTC) - datetime.fromisoformat(entered_at)).total_seconds(), 0.0)


def _alert_record(alert: dict[str, Any]) -> AlertRecord:
    return AlertRecord(
        id=alert["id"],
        severity=alert["severity"],
        status=alert["status"],
        summary=alert["summary"],
        event_id=alert.get("event_id"),
        created_at=alert["created_at"],
        resolved_at=alert.get("resolved_at"),
    )
