"""Composition root for the memory service's dependencies.

Wires the shared async session factory (`sentinel_common.db.session`) to
this service's concrete repositories, exposed as FastAPI dependencies.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from memory.core.config import Settings, get_settings
from memory.domain.repository import CameraRepository, EventRepository
from memory.infra.repositories import SqlAlchemyCameraRepository, SqlAlchemyEventRepository
from sentinel_common.db.session import build_session_factory
from sentinel_common.di import singleton

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_session_factory():  # noqa: ANN201 - inferred async_sessionmaker[AsyncSession]
    settings = get_settings()
    return build_session_factory(settings.database_url)


async def get_db_session(
    session_factory: Annotated[object, Depends(get_session_factory)],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:  # type: ignore[operator]
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_camera_repository(session: DbSessionDep) -> CameraRepository:
    return SqlAlchemyCameraRepository(session)


def get_event_repository(session: DbSessionDep) -> EventRepository:
    return SqlAlchemyEventRepository(session)


CameraRepositoryDep = Annotated[CameraRepository, Depends(get_camera_repository)]
EventRepositoryDep = Annotated[EventRepository, Depends(get_event_repository)]
