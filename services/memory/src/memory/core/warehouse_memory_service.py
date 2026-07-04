"""Composes the repositories into the memory service's actual API surface.

This is where "maintain current warehouse state" lives: `get_current_state`,
`get_recent_events`, and `get_entity_history` are read-only aggregations
over whatever's been recorded via `record_observation`/`record_zone_transition`/
`record_event`/`record_alert`. Nothing here is non-deterministic -- every
query is explicitly ordered and every "current" computation is a pure
function of an explicit `as_of` timestamp, not the wall clock, so the same
stored data always answers the same way.
"""

import uuid
from datetime import UTC, datetime

from sentinel_common.schemas.event import EventCreate, EventRead
from sentinel_common.schemas.zone import ZoneTransition, ZoneTransitionKind

from memory.domain.alert import AlertCreate, AlertRead
from memory.domain.entity import EntityObservation, EntityRead
from memory.domain.repository import (
    AlertRepository,
    EntityRepository,
    EventRepository,
    ZoneOccupancyRepository,
)
from memory.domain.state import EntityHistory, WarehouseState
from memory.domain.zone_occupancy import ZoneOccupancyRead


class EntityNotFoundError(Exception):
    """Raised when a zone transition references a track memory has never observed.

    A zone transition should always follow at least one prior observation
    of that (camera_id, track_id) -- if it doesn't, that's a genuine
    ordering/integration bug upstream, not something to paper over by
    silently creating a placeholder entity.
    """


class WarehouseMemoryService:
    def __init__(
        self,
        entities: EntityRepository,
        zone_occupancy: ZoneOccupancyRepository,
        events: EventRepository,
        alerts: AlertRepository,
        *,
        entity_staleness_seconds: float,
        default_recent_events_limit: int,
    ) -> None:
        self._entities = entities
        self._zone_occupancy = zone_occupancy
        self._events = events
        self._alerts = alerts
        self._entity_staleness_seconds = entity_staleness_seconds
        self._default_recent_events_limit = default_recent_events_limit

    # -- writes ---------------------------------------------------------

    async def record_observation(self, observation: EntityObservation) -> EntityRead:
        return await self._entities.record_observation(observation)

    async def record_zone_transition(self, transition: ZoneTransition) -> ZoneOccupancyRead | None:
        entity = await self._entities.get_by_track(transition.camera_id, transition.track_id)
        if entity is None:
            raise EntityNotFoundError(
                f"no entity recorded for camera={transition.camera_id} "
                f"track_id={transition.track_id}; record an observation first"
            )

        if transition.kind is ZoneTransitionKind.ENTERED:
            return await self._zone_occupancy.record_entered(
                entity_id=entity.id,
                warehouse_id=transition.warehouse_id,
                zone_id=transition.zone_id,
                zone_name=transition.zone_name,
                entered_at=transition.occurred_at,
            )
        return await self._zone_occupancy.record_exited(
            entity_id=entity.id, zone_id=transition.zone_id, exited_at=transition.occurred_at
        )

    async def record_event(self, event: EventCreate) -> EventRead:
        return await self._events.create(event)

    async def record_alert(self, alert: AlertCreate) -> AlertRead:
        return await self._alerts.create(alert)

    # -- reads ------------------------------------------------------------

    async def get_current_state(
        self,
        warehouse_id: uuid.UUID,
        *,
        as_of: datetime | None = None,
        recent_events_limit: int | None = None,
    ) -> WarehouseState:
        """A snapshot of `warehouse_id` as of `as_of` (defaults to now)."""
        generated_at = as_of if as_of is not None else datetime.now(UTC)
        entities = await self._entities.list_current(
            warehouse_id,
            as_of=generated_at,
            staleness_threshold_seconds=self._entity_staleness_seconds,
        )
        zone_occupancy = await self._zone_occupancy.list_current(warehouse_id)
        recent_events = await self._events.list_recent(
            warehouse_id, limit=recent_events_limit or self._default_recent_events_limit
        )
        active_alerts = await self._alerts.list_active(warehouse_id)

        return WarehouseState(
            warehouse_id=warehouse_id,
            generated_at=generated_at,
            entities=entities,
            zone_occupancy=zone_occupancy,
            recent_events=recent_events,
            active_alerts=active_alerts,
        )

    async def get_recent_events(
        self, warehouse_id: uuid.UUID, *, limit: int | None = None, before: datetime | None = None
    ) -> list[EventRead]:
        return await self._events.list_recent(
            warehouse_id, limit=limit or self._default_recent_events_limit, before=before
        )

    async def get_entity_history(self, entity_id: uuid.UUID) -> EntityHistory | None:
        entity = await self._entities.get(entity_id)
        if entity is None:
            return None

        zone_occupancy = await self._zone_occupancy.list_for_entity(entity_id)
        events = await self._events.list_for_track(entity.camera_id, entity.track_id)

        return EntityHistory(entity=entity, zone_occupancy=zone_occupancy, events=events)
