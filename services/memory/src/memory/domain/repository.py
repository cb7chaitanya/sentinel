"""Domain-level repository interfaces for structured warehouse memory.

`infra/repositories.py` implements these Protocols against SQLAlchemy; the
API layer depends only on the abstraction, keeping persistence details out
of route handlers.
"""

import uuid
from typing import Protocol

from sentinel_common.schemas.camera import CameraCreate, CameraRead
from sentinel_common.schemas.event import EventCreate, EventRead


class CameraRepository(Protocol):
    async def create(self, camera: CameraCreate) -> CameraRead: ...

    async def get(self, camera_id: uuid.UUID) -> CameraRead | None: ...

    async def list(self) -> list[CameraRead]: ...


class EventRepository(Protocol):
    async def create(self, event: EventCreate) -> EventRead: ...

    async def get(self, event_id: uuid.UUID) -> EventRead | None: ...

    async def list_for_camera(self, camera_id: uuid.UUID) -> list[EventRead]: ...
