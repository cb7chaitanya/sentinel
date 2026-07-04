"""Aggregate read models: the shapes `get_current_state`/`get_entity_history` return."""

import uuid
from datetime import datetime

from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.event import EventRead

from memory.domain.alert import AlertRead
from memory.domain.entity import EntityRead
from memory.domain.zone_occupancy import ZoneOccupancyRead


class WarehouseState(SentinelModel):
    """A snapshot of one warehouse as of `generated_at`."""

    warehouse_id: uuid.UUID
    generated_at: datetime
    entities: list[EntityRead]
    zone_occupancy: list[ZoneOccupancyRead]
    recent_events: list[EventRead]
    active_alerts: list[AlertRead]


class EntityHistory(SentinelModel):
    """Everything memory has recorded for one entity, oldest first."""

    entity: EntityRead
    zone_occupancy: list[ZoneOccupancyRead]
    events: list[EventRead]
