"""Schemas describing higher-level warehouse events derived from detections."""

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


class EventBase(SentinelModel):
    camera_id: uuid.UUID
    event_type: EventType
    occurred_at: datetime
    summary: str
    metadata: dict[str, str] = {}


class EventCreate(EventBase):
    pass


class EventRead(EventBase, TimestampedModel):
    pass
