import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
from sentinel_common.schemas.detection import FrameDetections
from sentinel_common.schemas.frame import Frame
from vision.core.detection_runner import DetectionPipelineRunner

CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _frame(sequence: int, camera_id: uuid.UUID = CAMERA_ID) -> Frame:
    return Frame(
        camera_id=camera_id, sequence=sequence, captured_at=T0, data=b"x", width=1, height=1
    )


class _FakeResponse:
    def __init__(self, json_body: object) -> None:
        self._json_body = json_body

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return self._json_body


class _FakeHttpClient:
    def __init__(self, camera_ids: list[uuid.UUID]) -> None:
        self._camera_ids = camera_ids

    async def get(self, url: str) -> _FakeResponse:
        return _FakeResponse([{"camera_id": str(c)} for c in self._camera_ids])


class _FailingHttpClient:
    async def get(self, url: str) -> _FakeResponse:
        raise httpx.ConnectError("boom")


class _FakePipeline:
    def __init__(self, fail_sequences: set[int] | None = None) -> None:
        self.processed: list[Frame] = []
        self._fail_sequences = fail_sequences or set()

    async def process(self, frame: Frame) -> FrameDetections:
        if frame.sequence in self._fail_sequences:
            raise RuntimeError("boom")
        self.processed.append(frame)
        return FrameDetections(
            camera_id=frame.camera_id, timestamp=frame.captured_at, detections=[]
        )


class _FakeEventsClient:
    def __init__(self) -> None:
        self.posted: list[FrameDetections] = []

    async def post_detections(self, frame_detections: FrameDetections) -> None:
        self.posted.append(frame_detections)


def _runner(
    http_client: object,
    pipeline: _FakePipeline,
    events: _FakeEventsClient,
    *,
    initial_backoff_seconds: float = 0.01,
    max_backoff_seconds: float = 0.05,
) -> DetectionPipelineRunner:
    return DetectionPipelineRunner(
        http_client,  # type: ignore[arg-type]
        pipeline,  # type: ignore[arg-type]
        events,  # type: ignore[arg-type]
        ingestion_service_url="http://ingestion:8001",
        initial_backoff_seconds=initial_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
    )


async def test_start_discovers_cameras_and_processes_frames_from_each(monkeypatch) -> None:
    async def fake_stream_frames(
        http_client: object, mjpeg_url: str, camera_id: uuid.UUID
    ) -> AsyncIterator[Frame]:
        yield _frame(1, camera_id)
        yield _frame(2, camera_id)
        await asyncio.Event().wait()  # a live stream never ends on its own

    monkeypatch.setattr("vision.core.detection_runner.stream_frames", fake_stream_frames)

    pipeline = _FakePipeline()
    events = _FakeEventsClient()
    runner = _runner(_FakeHttpClient([CAMERA_ID]), pipeline, events)

    await runner.start()
    await asyncio.sleep(0.05)
    await runner.stop()

    assert [f.sequence for f in pipeline.processed] == [1, 2]
    assert len(events.posted) == 2


async def test_a_stream_error_reconnects_and_keeps_processing(monkeypatch) -> None:
    attempts = 0

    async def fake_stream_frames(
        http_client: object, mjpeg_url: str, camera_id: uuid.UUID
    ) -> AsyncIterator[Frame]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("boom")
        yield _frame(1, camera_id)
        await asyncio.Event().wait()

    monkeypatch.setattr("vision.core.detection_runner.stream_frames", fake_stream_frames)

    pipeline = _FakePipeline()
    events = _FakeEventsClient()
    runner = _runner(_FakeHttpClient([CAMERA_ID]), pipeline, events)

    await runner.start()
    await asyncio.sleep(0.1)
    await runner.stop()

    assert attempts >= 2
    assert [f.sequence for f in pipeline.processed] == [1]


async def test_a_failing_frame_does_not_stop_the_camera_task(monkeypatch) -> None:
    async def fake_stream_frames(
        http_client: object, mjpeg_url: str, camera_id: uuid.UUID
    ) -> AsyncIterator[Frame]:
        yield _frame(1, camera_id)
        yield _frame(2, camera_id)
        await asyncio.Event().wait()

    monkeypatch.setattr("vision.core.detection_runner.stream_frames", fake_stream_frames)

    pipeline = _FakePipeline(fail_sequences={1})
    events = _FakeEventsClient()
    runner = _runner(_FakeHttpClient([CAMERA_ID]), pipeline, events)

    await runner.start()
    await asyncio.sleep(0.05)
    await runner.stop()

    assert [f.sequence for f in pipeline.processed] == [2]
    assert len(events.posted) == 1


async def test_discover_cameras_returns_empty_list_on_http_error() -> None:
    runner = _runner(_FailingHttpClient(), _FakePipeline(), _FakeEventsClient())

    cameras = await runner._discover_cameras()

    assert cameras == []
