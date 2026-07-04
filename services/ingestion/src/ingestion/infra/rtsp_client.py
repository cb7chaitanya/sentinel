"""OpenCV-backed implementation of `domain.camera.StreamReader`.

Stubbed out: no frame-capture logic yet, only the typed shape adapters must
fill in. Wiring this up to `cv2.VideoCapture` is tracked as follow-up work.
"""

from collections.abc import AsyncIterator

from ingestion.domain.camera import StreamReader


class RtspStreamReader(StreamReader):
    def __init__(self, rtsp_url: str) -> None:
        self._rtsp_url = rtsp_url

    async def frames(self) -> AsyncIterator[bytes]:
        raise NotImplementedError
        yield b""  # pragma: no cover - makes this an async generator for type-checkers

    async def close(self) -> None:
        raise NotImplementedError
