"""Domain-level interfaces for camera stream access.

Infra adapters (`infra/rtsp_client.py`) implement these Protocols so the API
layer and future orchestration logic can depend on an abstraction rather
than a concrete OpenCV/RTSP implementation.
"""

from collections.abc import AsyncIterator
from typing import Protocol

from sentinel_common.schemas.camera import CameraRead


class StreamReader(Protocol):
    """Reads frames from a single camera's RTSP stream."""

    async def frames(self) -> AsyncIterator[bytes]:
        """Yield raw encoded frames as they are captured."""
        ...

    async def close(self) -> None: ...


class CameraRegistry(Protocol):
    """Looks up configured cameras. Backed by the memory service in production."""

    async def get(self, camera_id: str) -> CameraRead | None: ...

    async def list_active(self) -> list[CameraRead]: ...
