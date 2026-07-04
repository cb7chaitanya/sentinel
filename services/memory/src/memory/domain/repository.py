"""Domain-level repository interfaces for structured warehouse memory.

`infra/repositories.py` implements these Protocols against SQLAlchemy; the
API layer and `core/warehouse_memory_service.py` depend only on the
abstraction, keeping persistence details out of route handlers and
business logic alike.
"""

import uuid
from datetime import datetime
from typing import Protocol

from sentinel_common.schemas.camera import CameraCreate, CameraRead
from sentinel_common.schemas.event import EventCreate, EventRead

from memory.domain.alert import AlertCreate, AlertRead, AlertStatus
from memory.domain.entity import EntityObservation, EntityRead, EntityType
from memory.domain.zone_occupancy import ZoneOccupancyRead


class CameraRepository(Protocol):
    async def create(self, camera: CameraCreate) -> CameraRead: ...

    async def get(self, camera_id: uuid.UUID) -> CameraRead | None: ...

    async def list(self) -> list[CameraRead]: ...


class EventRepository(Protocol):
    async def create(self, event: EventCreate) -> EventRead: ...

    async def get(self, event_id: uuid.UUID) -> EventRead | None: ...

    async def list_for_camera(self, camera_id: uuid.UUID) -> list[EventRead]: ...

    async def list_for_track(self, camera_id: uuid.UUID, track_id: int) -> list[EventRead]:
        """All events referencing one tracked entity, oldest first."""
        ...

    async def list_recent(
        self, warehouse_id: uuid.UUID, *, limit: int, before: datetime | None = None
    ) -> list[EventRead]:
        """Most recent events for a warehouse, newest first.

        `before`, if given, only returns events strictly earlier than it
        (cursor-style pagination: pass the last page's oldest
        `occurred_at` to get the next page).
        """
        ...


class EntityRepository(Protocol):
    """Tracked entities (workers, forklifts, pallets, boxes).

    `record_observation` upserts by `(camera_id, track_id)`: the first
    observation of a given track creates the entity, every subsequent one
    updates it in place -- there is only ever one row per tracked object.
    """

    async def record_observation(self, observation: EntityObservation) -> EntityRead: ...

    async def get(self, entity_id: uuid.UUID) -> EntityRead | None: ...

    async def get_by_track(self, camera_id: uuid.UUID, track_id: int) -> EntityRead | None: ...

    async def list_current(
        self,
        warehouse_id: uuid.UUID,
        *,
        as_of: datetime,
        staleness_threshold_seconds: float,
        entity_type: EntityType | None = None,
    ) -> list[EntityRead]:
        """Entities last seen within `staleness_threshold_seconds` of `as_of`."""
        ...


class ZoneOccupancyRepository(Protocol):
    """Zone occupancy intervals -- current (open) and historical (closed)."""

    async def record_entered(
        self,
        *,
        entity_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        zone_id: uuid.UUID,
        zone_name: str,
        entered_at: datetime,
    ) -> ZoneOccupancyRead: ...

    async def record_exited(
        self, *, entity_id: uuid.UUID, zone_id: uuid.UUID, exited_at: datetime
    ) -> ZoneOccupancyRead | None:
        """Close the open interval for `(entity_id, zone_id)`, if any.

        Returns `None` if there was no open interval to close (e.g. an
        exit recorded without a matching prior entry).
        """
        ...

    async def list_current(self, warehouse_id: uuid.UUID) -> list[ZoneOccupancyRead]:
        """Every open (`exited_at IS NULL`) interval in a warehouse."""
        ...

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[ZoneOccupancyRead]:
        """All intervals (open and closed) for one entity, oldest first."""
        ...


class AlertRepository(Protocol):
    async def create(self, alert: AlertCreate) -> AlertRead: ...

    async def get(self, alert_id: uuid.UUID) -> AlertRead | None: ...

    async def list_active(self, warehouse_id: uuid.UUID) -> list[AlertRead]:
        """Alerts not yet resolved (OPEN or ACKNOWLEDGED), newest first."""
        ...

    async def update_status(
        self,
        alert_id: uuid.UUID,
        status: AlertStatus,
        *,
        resolved_at: datetime | None = None,
    ) -> AlertRead | None: ...
