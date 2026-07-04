"""OpenCV-backed implementation of `domain.camera.StreamReader`.

`cv2.VideoCapture` treats RTSP streams, local webcams, and video files as the
same abstraction: something you open, read frames from, and that can stop
producing frames. That means one reconnect loop handles an RTSP disconnect,
a webcam unplug, and a video file reaching EOF -- reopening the same source
(which, for a file, means restarting from frame zero) is exactly the same
operation in all three cases, so there is no special-casing per source kind
beyond how the capture is opened.

`cv2.VideoCapture.read()` is a blocking, synchronous call with no built-in
cancellation, so every call into it is pushed onto a worker thread via
`asyncio.to_thread` to keep the event loop free. Calling `.release()` on a
capture while another thread is mid-`.read()` on that same capture is not
safe -- OpenCV/FFmpeg can deadlock rather than error out. So only the
`frames()` loop itself ever opens or releases `self._capture`; `close()`
never touches it directly. It just signals the loop (via an `asyncio.Event`,
which also cancels any in-progress reconnect backoff sleep immediately) and
relies on the loop's own `finally` block to release the capture once it next
gets control -- which, since reads are awaited before the loop checks the
event again, can never race a live `.read()` call. Callers that want the
underlying resource freed promptly should also stop consuming (or cancel
the task consuming) `frames()`; `StreamRegistry` does exactly that.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import cv2
import numpy as np
from sentinel_common.schemas.frame import Frame

from ingestion.domain.camera import (
    ConnectionState,
    StreamHealth,
    StreamReader,
    StreamSource,
    StreamSourceKind,
)
from ingestion.infra.stats import StreamStatsTracker

logger = logging.getLogger(__name__)

_JPEG_ENCODE_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), 90]


def _open_capture(source: StreamSource) -> cv2.VideoCapture | None:
    """Open a `cv2.VideoCapture` appropriate for the source kind.

    Runs on a worker thread (device/network I/O), so exceptions are caught
    and logged here rather than propagated -- the caller only needs to know
    whether it got a usable capture handle back.
    """
    try:
        if source.kind is StreamSourceKind.WEBCAM:
            capture = cv2.VideoCapture(int(source.uri))
        elif source.kind is StreamSourceKind.RTSP:
            capture = cv2.VideoCapture(source.uri, cv2.CAP_FFMPEG)
        else:
            capture = cv2.VideoCapture(source.uri)
    except (cv2.error, ValueError):
        logger.exception("failed to open capture for camera %s", source.camera_id)
        return None
    return capture


def _encode_jpeg(image: np.ndarray) -> tuple[bytes, int, int] | None:
    ok, buffer = cv2.imencode(".jpg", image, _JPEG_ENCODE_PARAMS)
    if not ok:
        return None
    height, width = image.shape[:2]
    return buffer.tobytes(), width, height


class OpenCvStreamReader:
    """Captures frames from a single `StreamSource`, reconnecting on failure."""

    def __init__(
        self,
        source: StreamSource,
        *,
        initial_backoff_seconds: float,
        max_backoff_seconds: float,
        max_consecutive_read_failures: int,
    ) -> None:
        self._source = source
        self._initial_backoff_seconds = initial_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._max_consecutive_read_failures = max_consecutive_read_failures

        self._capture: cv2.VideoCapture | None = None
        self._sequence = 0
        self._closed_event = asyncio.Event()
        self._stats = StreamStatsTracker(source.camera_id)

    async def frames(self) -> AsyncIterator[Frame]:
        backoff = self._initial_backoff_seconds
        consecutive_failures = 0

        try:
            while not self._closed_event.is_set():
                if self._capture is None:
                    if await self._try_connect():
                        backoff = self._initial_backoff_seconds
                        consecutive_failures = 0
                    else:
                        self._stats.set_state(ConnectionState.RECONNECTING)
                        await self._wait_before_retry(backoff)
                        backoff = min(backoff * 2, self._max_backoff_seconds)
                    continue

                ok, image = await asyncio.to_thread(self._capture.read)

                if not ok:
                    consecutive_failures += 1
                    if consecutive_failures >= self._max_consecutive_read_failures:
                        logger.warning(
                            "camera %s exceeded %d consecutive read failures, reconnecting",
                            self._source.camera_id,
                            self._max_consecutive_read_failures,
                        )
                        self._stats.record_reconnect()
                        await self._release_capture()
                    else:
                        self._stats.record_drop()
                    continue

                consecutive_failures = 0
                encoded = await asyncio.to_thread(_encode_jpeg, image)
                if encoded is None:
                    self._stats.record_drop()
                    continue

                data, width, height = encoded
                captured_at = datetime.now(UTC)
                self._sequence += 1
                self._stats.record_frame(captured_at)

                yield Frame(
                    camera_id=self._source.camera_id,
                    sequence=self._sequence,
                    captured_at=captured_at,
                    data=data,
                    width=width,
                    height=height,
                )
        finally:
            await self._release_capture()

    async def health(self) -> StreamHealth:
        return self._stats.snapshot()

    async def close(self) -> None:
        self._closed_event.set()
        self._stats.set_state(ConnectionState.STOPPED)

    async def _wait_before_retry(self, backoff: float) -> None:
        try:
            await asyncio.wait_for(self._closed_event.wait(), timeout=backoff)
        except TimeoutError:
            pass

    async def _try_connect(self) -> bool:
        self._stats.set_state(ConnectionState.CONNECTING)
        capture = await asyncio.to_thread(_open_capture, self._source)
        if capture is None or not capture.isOpened():
            if capture is not None:
                await asyncio.to_thread(capture.release)
            return False

        self._capture = capture
        self._stats.mark_connected(datetime.now(UTC))
        return True

    async def _release_capture(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            await asyncio.to_thread(capture.release)


class OpenCvStreamReaderFactory:
    """Builds `OpenCvStreamReader`s using the process's reconnect settings."""

    def __init__(
        self,
        *,
        initial_backoff_seconds: float,
        max_backoff_seconds: float,
        max_consecutive_read_failures: int,
    ) -> None:
        self._initial_backoff_seconds = initial_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._max_consecutive_read_failures = max_consecutive_read_failures

    def create(self, source: StreamSource) -> StreamReader:
        return OpenCvStreamReader(
            source,
            initial_backoff_seconds=self._initial_backoff_seconds,
            max_backoff_seconds=self._max_backoff_seconds,
            max_consecutive_read_failures=self._max_consecutive_read_failures,
        )
