"""SQLAlchemy-backed implementations of `domain.repository` Protocols.

Stubbed out: query/persistence logic is follow-up work.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from memory.domain.repository import CameraRepository, EventRepository
from sentinel_common.schemas.camera import CameraCreate, CameraRead
from sentinel_common.schemas.event import EventCreate, EventRead


class SqlAlchemyCameraRepository(CameraRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, camera: CameraCreate) -> CameraRead:
        raise NotImplementedError

    async def get(self, camera_id: uuid.UUID) -> CameraRead | None:
        raise NotImplementedError

    async def list(self) -> list[CameraRead]:
        raise NotImplementedError


class SqlAlchemyEventRepository(EventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: EventCreate) -> EventRead:
        raise NotImplementedError

    async def get(self, event_id: uuid.UUID) -> EventRead | None:
        raise NotImplementedError

    async def list_for_camera(self, camera_id: uuid.UUID) -> list[EventRead]:
        raise NotImplementedError
