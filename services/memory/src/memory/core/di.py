"""Composition root for the memory service's dependencies.

Wires the shared async session factory (`sentinel_common.db.session`) to
this service's concrete repositories, exposed as FastAPI dependencies.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sentinel_common.db.session import build_session_factory
from sentinel_common.di import singleton
from sqlalchemy.ext.asyncio import AsyncSession

from memory.core.config import Settings, get_settings
from memory.core.warehouse_memory_service import WarehouseMemoryService
from memory.domain.repository import (
    AlertRepository,
    CameraRepository,
    EntityRepository,
    EventRepository,
    ZoneOccupancyRepository,
)
from memory.infra.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyCameraRepository,
    SqlAlchemyEntityRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyZoneOccupancyRepository,
)

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


def get_entity_repository(session: DbSessionDep) -> EntityRepository:
    return SqlAlchemyEntityRepository(session)


def get_zone_occupancy_repository(session: DbSessionDep) -> ZoneOccupancyRepository:
    return SqlAlchemyZoneOccupancyRepository(session)


def get_alert_repository(session: DbSessionDep) -> AlertRepository:
    return SqlAlchemyAlertRepository(session)


CameraRepositoryDep = Annotated[CameraRepository, Depends(get_camera_repository)]
EventRepositoryDep = Annotated[EventRepository, Depends(get_event_repository)]
EntityRepositoryDep = Annotated[EntityRepository, Depends(get_entity_repository)]
ZoneOccupancyRepositoryDep = Annotated[
    ZoneOccupancyRepository, Depends(get_zone_occupancy_repository)
]
AlertRepositoryDep = Annotated[AlertRepository, Depends(get_alert_repository)]


def get_warehouse_memory_service(
    entities: EntityRepositoryDep,
    zone_occupancy: ZoneOccupancyRepositoryDep,
    events: EventRepositoryDep,
    alerts: AlertRepositoryDep,
    settings: SettingsDep,
) -> WarehouseMemoryService:
    return WarehouseMemoryService(
        entities,
        zone_occupancy,
        events,
        alerts,
        entity_staleness_seconds=settings.entity_staleness_seconds,
        default_recent_events_limit=settings.default_recent_events_limit,
    )


WarehouseMemoryServiceDep = Annotated[
    WarehouseMemoryService, Depends(get_warehouse_memory_service)
]
