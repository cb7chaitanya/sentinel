import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ingestion.core.di import get_stream_registry
from ingestion.domain.camera import ConnectionState, StreamHealth
from ingestion.main import app

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
