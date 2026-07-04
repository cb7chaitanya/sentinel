"""Domain-level interfaces and value objects for camera stream capture.

`infra/opencv_capture.py` implements `StreamReader` and `StreamReaderFactory`
against OpenCV; the stream registry and API layer depend only on these
abstractions, never on OpenCV directly, so the capture backend could be
swapped (e.g. for a native RTSP/WebRTC client) without touching them.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import Field
from sentinel_common.schemas.camera import CameraRead
from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.frame import Frame


class StreamSourceKind(StrEnum):
    RTSP = "rtsp"
    WEBCAM = "webcam"
    FILE = "file"


class StreamSource(SentinelModel):
    """Identifies where a single camera's frames come from.

    `uri` is interpreted according to `kind`: an `rtsp://` URL for RTSP, a
    local device index (as a string, e.g. "0") for a webcam, or a filesystem
    path for a video file.
    """

    camera_id: uuid.UUID
    kind: StreamSourceKind
    uri: str


class ConnectionState(StrEnum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"


class StreamHealth(SentinelModel):
    """Point-in-time health and throughput snapshot for one stream."""

    camera_id: uuid.UUID
    state: ConnectionState
    fps: float = Field(ge=0.0)
    frames_read: int = Field(ge=0)
    frames_dropped: int = Field(ge=0)
    reconnect_count: int = Field(ge=0)
    last_frame_at: datetime | None
    connected_since: datetime | None


class StreamReader(Protocol):
    """Reads frames from a single camera source, reconnecting on failure."""

    def frames(self) -> AsyncIterator[Frame]:
        """Yield frames as they are captured until `close()` is called.

        Never raises on transient capture failures -- those are retried or
        reconnected internally and reflected in `health()` instead.
        """
        ...

    async def health(self) -> StreamHealth:
        """Return the current connection health/throughput snapshot."""
        ...

    async def close(self) -> None:
        """Stop capturing and release the underlying resource."""
        ...


class StreamReaderFactory(Protocol):
    """Builds a `StreamReader` for a given camera source."""

    def create(self, source: StreamSource) -> StreamReader: ...


class CameraRegistry(Protocol):
    """Looks up configured cameras. Backed by the memory service in production."""

    async def get(self, camera_id: str) -> CameraRead | None: ...

    async def list_active(self) -> list[CameraRead]: ...
