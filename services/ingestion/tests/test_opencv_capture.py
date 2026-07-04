import asyncio
import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest
from ingestion.domain.camera import ConnectionState, StreamSource, StreamSourceKind
from ingestion.infra.opencv_capture import (
    OpenCvStreamReader,
    OpenCvStreamReaderFactory,
    _open_capture,
)

CAMERA_ID = uuid.uuid4()


def _make_test_video(path: Path, *, frame_count: int, size: tuple[int, int] = (32, 24)) -> None:
    width, height = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (width, height))
    for i in range(frame_count):
        frame = np.full((height, width, 3), fill_value=i % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()


@pytest.fixture
def video_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.mp4"
    _make_test_video(path, frame_count=5)
    return path


async def test_reads_frames_from_a_video_file(video_file: Path) -> None:
    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.FILE, uri=str(video_file))
    reader = OpenCvStreamReader(
        source,
        initial_backoff_seconds=0.01,
        max_backoff_seconds=0.05,
        max_consecutive_read_failures=3,
    )

    frames = []
    async for frame in reader.frames():
        frames.append(frame)
        if len(frames) == 5:
            break
    await reader.close()

    assert [f.sequence for f in frames] == [1, 2, 3, 4, 5]
    assert all(f.camera_id == CAMERA_ID for f in frames)
    assert all(f.data for f in frames)
    assert frames[0].width == 32
    assert frames[0].height == 24

    health = await reader.health()
    assert health.frames_read == 5
    assert health.state is ConnectionState.STOPPED


async def test_reopens_video_file_after_eof_like_a_reconnect(video_file: Path) -> None:
    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.FILE, uri=str(video_file))
    reader = OpenCvStreamReader(
        source,
        initial_backoff_seconds=0.01,
        max_backoff_seconds=0.05,
        max_consecutive_read_failures=1,
    )

    frames = []
    async for frame in reader.frames():
        frames.append(frame)
        if len(frames) == 7:  # more than the file's 5 frames -> must loop
            break
    await reader.close()

    assert len(frames) == 7
    # Sequence keeps counting up across the reopen; only the underlying
    # capture position resets, not the reader's own frame numbering.
    assert [f.sequence for f in frames] == list(range(1, 8))
    health = await reader.health()
    assert health.reconnect_count >= 1


async def test_close_stops_iteration_promptly(video_file: Path) -> None:
    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.FILE, uri=str(video_file))
    reader = OpenCvStreamReader(
        source,
        initial_backoff_seconds=0.01,
        max_backoff_seconds=0.05,
        max_consecutive_read_failures=3,
    )
    consumed = 0

    async def consume() -> None:
        nonlocal consumed
        async for _ in reader.frames():
            consumed += 1

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await reader.close()
    await asyncio.wait_for(task, timeout=1.0)

    assert consumed > 0


def test_open_capture_dispatches_webcam_device_index(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_video_capture(*args: object, **kwargs: object) -> object:
        seen["args"] = args
        return object()

    monkeypatch.setattr(cv2, "VideoCapture", fake_video_capture)

    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.WEBCAM, uri="2")
    _open_capture(source)

    assert seen["args"] == (2,)


def test_open_capture_dispatches_rtsp_with_ffmpeg_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_video_capture(*args: object, **kwargs: object) -> object:
        seen["args"] = args
        return object()

    monkeypatch.setattr(cv2, "VideoCapture", fake_video_capture)

    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.RTSP, uri="rtsp://camera.local/stream")
    _open_capture(source)

    assert seen["args"] == ("rtsp://camera.local/stream", cv2.CAP_FFMPEG)


def test_open_capture_returns_none_on_invalid_webcam_index() -> None:
    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.WEBCAM, uri="not-a-number")

    assert _open_capture(source) is None


async def test_reconnect_backoff_retries_until_connect_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    class FakeCapture:
        def __init__(self, ok: bool) -> None:
            self._ok = ok

        def isOpened(self) -> bool:
            return self._ok

        def release(self) -> None:
            pass

        def read(self) -> tuple[bool, np.ndarray]:
            return True, np.zeros((4, 4, 3), dtype=np.uint8)

    def fake_open(source: StreamSource) -> FakeCapture:
        attempts["count"] += 1
        return FakeCapture(ok=attempts["count"] >= 3)

    import ingestion.infra.opencv_capture as capture_module

    monkeypatch.setattr(capture_module, "_open_capture", fake_open)

    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.WEBCAM, uri="0")
    reader = OpenCvStreamReader(
        source,
        initial_backoff_seconds=0.001,
        max_backoff_seconds=0.01,
        max_consecutive_read_failures=3,
    )

    frames = []
    async for frame in reader.frames():
        frames.append(frame)
        break
    await reader.close()

    assert attempts["count"] == 3
    assert len(frames) == 1


def test_factory_creates_a_working_stream_reader() -> None:
    factory = OpenCvStreamReaderFactory(
        initial_backoff_seconds=1.0,
        max_backoff_seconds=30.0,
        max_consecutive_read_failures=5,
    )
    source = StreamSource(camera_id=CAMERA_ID, kind=StreamSourceKind.FILE, uri="/nonexistent.mp4")

    reader = factory.create(source)

    assert hasattr(reader, "frames")
    assert hasattr(reader, "health")
    assert hasattr(reader, "close")
