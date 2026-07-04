"""SQLAlchemy-backed implementations of `domain.repository` Protocols.

Each write method commits its own unit of work -- there's no multi-step
transaction anywhere in this service that needs a shared unit-of-work
across repositories, so per-method commits keep things simple rather than
adding a transaction-coordination layer nothing here needs yet.
"""

import uuid
from datetime import datetime, timedelta

from sentinel_common.schemas.camera import CameraCreate, CameraRead
from sentinel_common.schemas.detection import BoundingBox, Velocity
from sentinel_common.schemas.event import EventCreate, EventRead
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from memory.domain.alert import AlertCreate, AlertRead, AlertStatus
from memory.domain.entity import EntityObservation, EntityRead, EntityType, classify_entity_type
from memory.domain.repository import (
    AlertRepository,
    CameraRepository,
    EntityRepository,
    EventRepository,
    ZoneOccupancyRepository,
)
from memory.domain.zone_occupancy import ZoneOccupancyRead
from memory.infra.models import Alert, Entity, Event, ZoneOccupancy


class SqlAlchemyCameraRepository(CameraRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, camera: CameraCreate) -> CameraRead:
        raise NotImplementedError

    async def get(self, camera_id: uuid.UUID) -> CameraRead | None:
        raise NotImplementedError

    async def list(self) -> list[CameraRead]:
        raise NotImplementedError


def _entity_to_read(row: Entity) -> EntityRead:
    return EntityRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        warehouse_id=row.warehouse_id,
        camera_id=row.camera_id,
        track_id=row.track_id,
        entity_type=EntityType(row.entity_type),
        label=row.label,
        bounding_box=BoundingBox(
            x_min=row.bbox_x_min, y_min=row.bbox_y_min, x_max=row.bbox_x_max, y_max=row.bbox_y_max
        ),
        velocity=(
            Velocity(vx=row.velocity_vx, vy=row.velocity_vy)
            if row.velocity_vx is not None and row.velocity_vy is not None
            else None
        ),
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
    )


class SqlAlchemyEntityRepository(EntityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_observation(self, observation: EntityObservation) -> EntityRead:
        entity_type = classify_entity_type(observation.label)
        values = {
            "warehouse_id": observation.warehouse_id,
            "camera_id": observation.camera_id,
            "track_id": observation.track_id,
            "entity_type": entity_type.value,
            "label": observation.label,
            "bbox_x_min": observation.bounding_box.x_min,
            "bbox_y_min": observation.bounding_box.y_min,
            "bbox_x_max": observation.bounding_box.x_max,
            "bbox_y_max": observation.bounding_box.y_max,
            "velocity_vx": observation.velocity.vx if observation.velocity else None,
            "velocity_vy": observation.velocity.vy if observation.velocity else None,
            "first_seen_at": observation.observed_at,
            "last_seen_at": observation.observed_at,
        }
        stmt = pg_insert(Entity).values(**values)
        # Later observations of the same (camera_id, track_id) overwrite
        # everything except first_seen_at. Assumes observations for a given
        # track arrive in order, which holds for today's single-writer-
        # per-camera pipeline; out-of-order delivery would need
        # last-write-wins-by-timestamp conflict resolution instead.
        update_columns: dict[str, object] = {
            key: stmt.excluded[key]
            for key in values
            if key not in ("warehouse_id", "camera_id", "track_id", "first_seen_at")
        }
        # onupdate=func.now() on the model only fires for ORM-driven
        # updates; this is a Core-style upsert, so updated_at needs setting
        # explicitly here too.
        update_columns["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=["camera_id", "track_id"],
            set_=update_columns,
        ).returning(Entity)
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        await self._session.commit()
        return _entity_to_read(row)

    async def get(self, entity_id: uuid.UUID) -> EntityRead | None:
        row = await self._session.get(Entity, entity_id)
        return _entity_to_read(row) if row else None

    async def get_by_track(self, camera_id: uuid.UUID, track_id: int) -> EntityRead | None:
        stmt = select(Entity).where(Entity.camera_id == camera_id, Entity.track_id == track_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _entity_to_read(row) if row else None

    async def list_current(
        self,
        warehouse_id: uuid.UUID,
        *,
        as_of: datetime,
        staleness_threshold_seconds: float,
        entity_type: EntityType | None = None,
    ) -> list[EntityRead]:
        earliest_last_seen = as_of - timedelta(seconds=staleness_threshold_seconds)
        stmt = (
            select(Entity)
            .where(Entity.warehouse_id == warehouse_id, Entity.last_seen_at >= earliest_last_seen)
            .order_by(Entity.last_seen_at.desc(), Entity.id)
        )
        if entity_type is not None:
            stmt = stmt.where(Entity.entity_type == entity_type.value)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_entity_to_read(row) for row in rows]


def _zone_occupancy_to_read(row: ZoneOccupancy) -> ZoneOccupancyRead:
    return ZoneOccupancyRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        warehouse_id=row.warehouse_id,
        zone_id=row.zone_id,
        zone_name=row.zone_name,
        entity_id=row.entity_id,
        entered_at=row.entered_at,
        exited_at=row.exited_at,
    )


class SqlAlchemyZoneOccupancyRepository(ZoneOccupancyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_entered(
        self,
        *,
        entity_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        zone_id: uuid.UUID,
        zone_name: str,
        entered_at: datetime,
    ) -> ZoneOccupancyRead:
        row = ZoneOccupancy(
            warehouse_id=warehouse_id,
            zone_id=zone_id,
            zone_name=zone_name,
            entity_id=entity_id,
            entered_at=entered_at,
            exited_at=None,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _zone_occupancy_to_read(row)

    async def record_exited(
        self, *, entity_id: uuid.UUID, zone_id: uuid.UUID, exited_at: datetime
    ) -> ZoneOccupancyRead | None:
        stmt = (
            select(ZoneOccupancy)
            .where(
                ZoneOccupancy.entity_id == entity_id,
                ZoneOccupancy.zone_id == zone_id,
                ZoneOccupancy.exited_at.is_(None),
            )
            .order_by(ZoneOccupancy.entered_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        row.exited_at = exited_at
        await self._session.commit()
        await self._session.refresh(row)
        return _zone_occupancy_to_read(row)

    async def list_current(self, warehouse_id: uuid.UUID) -> list[ZoneOccupancyRead]:
        stmt = (
            select(ZoneOccupancy)
            .where(ZoneOccupancy.warehouse_id == warehouse_id, ZoneOccupancy.exited_at.is_(None))
            .order_by(ZoneOccupancy.entered_at, ZoneOccupancy.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_zone_occupancy_to_read(row) for row in rows]

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[ZoneOccupancyRead]:
        stmt = (
            select(ZoneOccupancy)
            .where(ZoneOccupancy.entity_id == entity_id)
            .order_by(ZoneOccupancy.entered_at, ZoneOccupancy.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_zone_occupancy_to_read(row) for row in rows]


def _event_to_read(row: Event) -> EventRead:
    return EventRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        warehouse_id=row.warehouse_id,
        camera_id=row.camera_id,
        event_type=row.event_type,
        occurred_at=row.occurred_at,
        summary=row.summary,
        track_id=row.track_id,
        zone_id=row.zone_id,
        zone_name=row.zone_name,
        dwell_time_seconds=row.dwell_time_seconds,
        related_track_id=row.related_track_id,
        related_label=row.related_label,
    )


class SqlAlchemyEventRepository(EventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: EventCreate) -> EventRead:
        row = Event(
            warehouse_id=event.warehouse_id,
            camera_id=event.camera_id,
            event_type=event.event_type.value,
            occurred_at=event.occurred_at,
            summary=event.summary,
            track_id=event.track_id,
            zone_id=event.zone_id,
            zone_name=event.zone_name,
            dwell_time_seconds=event.dwell_time_seconds,
            related_track_id=event.related_track_id,
            related_label=event.related_label,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _event_to_read(row)

    async def get(self, event_id: uuid.UUID) -> EventRead | None:
        row = await self._session.get(Event, event_id)
        return _event_to_read(row) if row else None

    async def list_for_camera(self, camera_id: uuid.UUID) -> list[EventRead]:
        stmt = (
            select(Event)
            .where(Event.camera_id == camera_id)
            .order_by(Event.occurred_at, Event.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_event_to_read(row) for row in rows]

    async def list_for_track(self, camera_id: uuid.UUID, track_id: int) -> list[EventRead]:
        stmt = (
            select(Event)
            .where(Event.camera_id == camera_id, Event.track_id == track_id)
            .order_by(Event.occurred_at, Event.id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_event_to_read(row) for row in rows]

    async def list_recent(
        self, warehouse_id: uuid.UUID, *, limit: int, before: datetime | None = None
    ) -> list[EventRead]:
        stmt = select(Event).where(Event.warehouse_id == warehouse_id)
        if before is not None:
            stmt = stmt.where(Event.occurred_at < before)
        stmt = stmt.order_by(Event.occurred_at.desc(), Event.id.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_event_to_read(row) for row in rows]


def _alert_to_read(row: Alert) -> AlertRead:
    return AlertRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        warehouse_id=row.warehouse_id,
        camera_id=row.camera_id,
        event_id=row.event_id,
        severity=row.severity,
        status=row.status,
        summary=row.summary,
        resolved_at=row.resolved_at,
    )


class SqlAlchemyAlertRepository(AlertRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, alert: AlertCreate) -> AlertRead:
        row = Alert(
            warehouse_id=alert.warehouse_id,
            camera_id=alert.camera_id,
            event_id=alert.event_id,
            severity=alert.severity.value,
            status=AlertStatus.OPEN.value,
            summary=alert.summary,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _alert_to_read(row)

    async def get(self, alert_id: uuid.UUID) -> AlertRead | None:
        row = await self._session.get(Alert, alert_id)
        return _alert_to_read(row) if row else None

    async def list_active(self, warehouse_id: uuid.UUID) -> list[AlertRead]:
        stmt = (
            select(Alert)
            .where(Alert.warehouse_id == warehouse_id, Alert.status != AlertStatus.RESOLVED.value)
            .order_by(Alert.created_at.desc(), Alert.id.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_alert_to_read(row) for row in rows]

    async def update_status(
        self,
        alert_id: uuid.UUID,
        status: AlertStatus,
        *,
        resolved_at: datetime | None = None,
    ) -> AlertRead | None:
        row = await self._session.get(Alert, alert_id)
        if row is None:
            return None
        row.status = status.value
        row.resolved_at = resolved_at
        await self._session.commit()
        await self._session.refresh(row)
        return _alert_to_read(row)
