import uuid
from datetime import UTC, datetime

from events.core.di import get_detection_ingest_service
from events.main import app
from fastapi.testclient import TestClient
from sentinel_common.schemas.detection import FrameDetections

CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeIngestService:
    def __init__(self) -> None:
        self.received: list[FrameDetections] = []

    async def ingest(self, frame_detections: FrameDetections) -> None:
        self.received.append(frame_detections)


def test_ingest_detections_hands_the_payload_to_the_ingest_service() -> None:
    fake = _FakeIngestService()
    app.dependency_overrides[get_detection_ingest_service] = lambda: fake
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/detections",
            json={"camera_id": str(CAMERA_ID), "timestamp": T0.isoformat(), "detections": []},
        )
    finally:
        app.dependency_overrides.pop(get_detection_ingest_service, None)

    assert response.status_code == 202
    assert len(fake.received) == 1
    assert fake.received[0].camera_id == CAMERA_ID
