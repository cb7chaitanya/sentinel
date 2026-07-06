import uuid
from datetime import UTC, datetime

import httpx
import pytest
from events.infra.memory_client import MemoryClient
from sentinel_common.schemas.detection import BoundingBox
from sentinel_common.schemas.entity import EntityObservation
from sentinel_common.schemas.event import EventCreate, EventType
from sentinel_common.schemas.zone import ZoneTransition, ZoneTransitionKind

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _client(handler) -> MemoryClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return MemoryClient(http_client=http_client, base_url="http://memory:8004")


async def test_record_observation_posts_to_the_observations_endpoint() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content
        return httpx.Response(201, json={})

    observation = EntityObservation(
        warehouse_id=WAREHOUSE_ID,
        camera_id=CAMERA_ID,
        track_id=1,
        label="pallet",
        bounding_box=BoundingBox(x_min=0, y_min=0, x_max=1, y_max=1),
        observed_at=T0,
    )

    await _client(handler).record_observation(observation)

    assert seen["path"] == "/api/v1/observations"
    assert b'"track_id":1' in seen["body"]


async def test_record_zone_transition_posts_to_the_zone_transitions_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/zone-transitions"
        return httpx.Response(201, json=None)

    transition = ZoneTransition(
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        camera_id=CAMERA_ID,
        track_id=1,
        kind=ZoneTransitionKind.ENTERED,
        occurred_at=T0,
    )

    await _client(handler).record_zone_transition(transition)


async def test_record_event_posts_to_the_events_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/events"
        return httpx.Response(201, json={})

    event = EventCreate(
        camera_id=CAMERA_ID,
        event_type=EventType.OBJECT_MOVED,
        occurred_at=T0,
        summary="Pallet moved",
    )

    await _client(handler).record_event(event)


async def test_raises_for_non_2xx_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "no entity"})

    transition = ZoneTransition(
        warehouse_id=WAREHOUSE_ID,
        zone_id=ZONE_ID,
        zone_name="Loading Dock",
        camera_id=CAMERA_ID,
        track_id=1,
        kind=ZoneTransitionKind.ENTERED,
        occurred_at=T0,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await _client(handler).record_zone_transition(transition)
