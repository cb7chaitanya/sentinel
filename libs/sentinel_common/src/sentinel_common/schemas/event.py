"""Schemas describing higher-level warehouse events derived from detections.

The `ZONE_BREACH`/`LOITERING`/`FORKLIFT_PROXIMITY`/`PPE_VIOLATION`/
`DWELL_TIME_EXCEEDED` kinds are alert-style business rules (a specific
zone or condition someone cares about). `ZONE_ENTERED`/`ZONE_EXITED`/
`OBJECT_MOVED`/`OBJECT_STOPPED`/`OBJECT_PICKED` are the neutral activity
stream the Event Engine produces from continuous object observations --
"Forklift entered Loading Dock", "Worker picked pallet" -- regardless of
whether any given occurrence is actually interesting to alert on.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel, TimestampedModel


class EventType(StrEnum):
    ZONE_BREACH = "zone_breach"
    LOITERING = "loitering"
    FORKLIFT_PROXIMITY = "forklift_proximity"
    PPE_VIOLATION = "ppe_violation"
    DWELL_TIME_EXCEEDED = "dwell_time_exceeded"

    ZONE_ENTERED = "zone_entered"
    ZONE_EXITED = "zone_exited"
    OBJECT_MOVED = "object_moved"
    OBJECT_STOPPED = "object_stopped"
    OBJECT_PICKED = "object_picked"


class EventBase(SentinelModel):
    camera_id: uuid.UUID
    event_type: EventType
    occurred_at: datetime
    summary: str

    # Optional because not every producer can resolve it: a zone-derived
    # event (ZONE_ENTERED/EXITED) knows its warehouse via the zone, but a
    # plain motion event has no camera->warehouse registry to consult yet.
    warehouse_id: uuid.UUID | None = None

    # Strongly-typed detail fields, populated according to event_type --
    # kept as explicit typed fields (not a free-form dict) so consumers
    # never need to parse anything out of `summary` or `metadata`.
    track_id: int | None = None
    zone_id: uuid.UUID | None = None
    zone_name: str | None = None
    dwell_time_seconds: float | None = None
    related_track_id: int | None = None
    related_label: str | None = None

    metadata: dict[str, str] = {}


class EventCreate(EventBase):
    pass


class EventRead(EventBase, TimestampedModel):
    pass
