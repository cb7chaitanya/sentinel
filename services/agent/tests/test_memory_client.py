import uuid

import httpx
import pytest
from agent.infra.memory_client import MemoryClient

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()
ALERT_ID = uuid.uuid4()
T0 = "2026-01-01T00:00:00+00:00"


def _entity_json(**overrides: object) -> dict:
    data = {
        "id": str(ENTITY_ID),
        "warehouse_id": str(WAREHOUSE_ID),
        "camera_id": str(CAMERA_ID),
        "track_id": 1,
        "entity_type": "pallet",
        "label": "pallet",
        "bounding_box": {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
        "velocity": None,
        "first_seen_at": T0,
        "last_seen_at": T0,
        "created_at": T0,
        "updated_at": T0,
    }
    data.update(overrides)
    return data


def _event_json(**overrides: object) -> dict:
    data = {
        "id": str(EVENT_ID),
        "camera_id": str(CAMERA_ID),
        "event_type": "zone_entered",
        "occurred_at": T0,
        "summary": "Pallet entered Zone B",
        "warehouse_id": str(WAREHOUSE_ID),
        "track_id": 1,
        "zone_id": None,
        "zone_name": "Zone B",
        "dwell_time_seconds": None,
        "related_track_id": None,
        "related_label": None,
        "metadata": {},
        "created_at": T0,
        "updated_at": T0,
    }
    data.update(overrides)
    return data


def _alert_json(**overrides: object) -> dict:
    data = {
        "id": str(ALERT_ID),
        "warehouse_id": str(WAREHOUSE_ID),
        "camera_id": str(CAMERA_ID),
        "event_id": str(EVENT_ID),
        "severity": "high",
        "summary": "Dwell time exceeded",
        "status": "open",
        "resolved_at": None,
        "created_at": T0,
        "updated_at": T0,
    }
    data.update(overrides)
    return data


def _zone_occupancy_json(**overrides: object) -> dict:
    data = {
        "id": str(uuid.uuid4()),
        "warehouse_id": str(WAREHOUSE_ID),
        "zone_id": str(uuid.uuid4()),
        "zone_name": "Zone B",
        "entity_id": str(ENTITY_ID),
        "entered_at": T0,
        "exited_at": None,
        "created_at": T0,
        "updated_at": T0,
    }
    data.update(overrides)
    return data


def _client(handler) -> MemoryClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return MemoryClient(http_client=http_client, base_url="http://memory:8004")


async def test_get_current_snapshot_maps_state_and_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/api/v1/state/{WAREHOUSE_ID}":
            return httpx.Response(
                200,
                json={
                    "warehouse_id": str(WAREHOUSE_ID),
                    "generated_at": T0,
                    "entities": [_entity_json()],
                    "zone_occupancy": [_zone_occupancy_json()],
                    "recent_events": [],
                    "active_alerts": [_alert_json()],
                },
            )
        assert request.url.path == "/api/v1/events"
        assert request.url.params["warehouse_id"] == str(WAREHOUSE_ID)
        return httpx.Response(200, json=[_event_json()])

    client = _client(handler)

    snapshot = await client.get_current_snapshot(WAREHOUSE_ID)

    assert len(snapshot.entities) == 1
    entity = snapshot.entities[0]
    assert entity.entity_id == ENTITY_ID
    assert [z.zone_name for z in entity.current_zones] == ["Zone B"]
    assert [e.id for e in snapshot.events] == [EVENT_ID]
    assert [a.id for a in snapshot.alerts] == [ALERT_ID]


async def test_get_entity_history_returns_entity_and_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/entities/{ENTITY_ID}/history"
        return httpx.Response(
            200,
            json={
                "entity": _entity_json(),
                "zone_occupancy": [_zone_occupancy_json()],
                "events": [_event_json()],
            },
        )

    client = _client(handler)

    result = await client.get_entity_history(ENTITY_ID)

    assert result is not None
    entity, events = result
    assert entity.entity_id == ENTITY_ID
    assert [e.id for e in events] == [EVENT_ID]


async def test_get_entity_history_returns_none_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = _client(handler)

    result = await client.get_entity_history(uuid.uuid4())

    assert result is None


async def test_get_alert_returns_alert_record() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/alerts/{ALERT_ID}"
        return httpx.Response(200, json=_alert_json())

    client = _client(handler)

    alert = await client.get_alert(ALERT_ID)

    assert alert is not None
    assert alert.id == ALERT_ID
    assert alert.event_id == EVENT_ID


async def test_get_alert_returns_none_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = _client(handler)

    alert = await client.get_alert(uuid.uuid4())

    assert alert is None


async def test_get_event_returns_event() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/events/{EVENT_ID}"
        return httpx.Response(200, json=_event_json())

    client = _client(handler)

    event = await client.get_event(EVENT_ID)

    assert event is not None
    assert event.id == EVENT_ID


async def test_get_event_returns_none_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = _client(handler)

    event = await client.get_event(uuid.uuid4())

    assert event is None


async def test_raises_for_non_404_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    client = _client(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_alert(uuid.uuid4())
