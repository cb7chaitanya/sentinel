import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sentinel_common.schemas.detection import FrameDetections
from vision.infra.events_client import EventsClient

CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _client(handler) -> EventsClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return EventsClient(http_client=http_client, base_url="http://events:8003")


async def test_post_detections_posts_to_the_detections_endpoint() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content
        return httpx.Response(202)

    frame_detections = FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[])

    await _client(handler).post_detections(frame_detections)

    assert seen["path"] == "/api/v1/detections"
    assert str(CAMERA_ID).encode() in seen["body"]


async def test_raises_for_non_2xx_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"boom")

    frame_detections = FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[])

    with pytest.raises(httpx.HTTPStatusError):
        await _client(handler).post_detections(frame_detections)
