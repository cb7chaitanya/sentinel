import asyncio
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from ingestion.api.v1.streams import _mjpeg_parts
from ingestion.core.di import get_stream_registry
from ingestion.core.frame_broadcaster import FrameBroadcaster
from ingestion.domain.camera import ConnectionState, StreamHealth
from ingestion.main import app
from sentinel_common.schemas.frame import Frame

CAMERA_ID = uuid.uuid4()


class FakeStreamRegistry:
    async def list_health(self) -> list[StreamHealth]:
        return [
            StreamHealth(
                camera_id=CAMERA_ID,
                state=ConnectionState.CONNECTED,
                fps=12.5,
                frames_read=100,
                frames_dropped=2,
                reconnect_count=1,
                last_frame_at=datetime.now(UTC),
                connected_since=datetime.now(UTC),
            )
        ]

    async def health(self, camera_id: uuid.UUID) -> StreamHealth | None:
        if camera_id != CAMERA_ID:
            return None
        healths = await self.list_health()
        return healths[0]


def test_list_streams_returns_configured_stream_health() -> None:
    app.dependency_overrides[get_stream_registry] = FakeStreamRegistry
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/streams")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["camera_id"] == str(CAMERA_ID)
    assert body[0]["state"] == "connected"
    assert body[0]["frames_dropped"] == 2


def test_get_stream_health_for_known_camera() -> None:
    app.dependency_overrides[get_stream_registry] = FakeStreamRegistry
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/streams/{CAMERA_ID}/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["camera_id"] == str(CAMERA_ID)


def test_get_stream_health_for_unknown_camera_is_404() -> None:
    app.dependency_overrides[get_stream_registry] = FakeStreamRegistry
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/streams/{uuid.uuid4()}/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_mjpeg_stream_for_unknown_camera_is_404() -> None:
    app.dependency_overrides[get_stream_registry] = FakeStreamRegistry
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/streams/{uuid.uuid4()}/mjpeg")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


async def test_mjpeg_parts_yields_a_multipart_jpeg_boundary_per_published_frame() -> None:
    # Exercises the streaming generator directly rather than through a real
    # HTTP round trip: an MJPEG stream never terminates on its own, and
    # httpx's ASGITransport fully buffers a response body before returning
    # it, so driving this through an actual client.stream() call would just
    # hang forever waiting for a response that's never "complete".
    broadcaster = FrameBroadcaster()
    frame = Frame(
        camera_id=CAMERA_ID,
        sequence=1,
        captured_at=datetime.now(UTC),
        data=b"not-really-a-jpeg",
        width=1,
        height=1,
    )

    parts = _mjpeg_parts(broadcaster, CAMERA_ID)
    pending = asyncio.ensure_future(parts.__anext__())
    await asyncio.sleep(0)  # let the generator reach `await queue.get()` and subscribe

    broadcaster.publish(frame)
    chunk = await asyncio.wait_for(pending, timeout=1.0)

    await parts.aclose()

    assert chunk.startswith(b"--sentinelframe\r\n")
    assert b"Content-Type: image/jpeg\r\n" in chunk
    assert chunk.endswith(b"not-really-a-jpeg\r\n")
