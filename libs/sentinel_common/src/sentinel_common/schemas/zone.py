"""Schemas describing zone occupancy transitions produced by the events service.

A zone's polygon/geometry configuration is not a cross-service wire format
-- it stays local to the events service (see
`services/events/src/events/domain/zone.py`). `ZoneTransition` is the
boundary artifact: the structured event the Zone Engine actually emits
when a tracked object enters or exits a zone.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel


class ZoneTransitionKind(StrEnum):
    ENTERED = "entered"
    EXITED = "exited"


class ZoneTransition(SentinelModel):
    warehouse_id: uuid.UUID
    zone_id: uuid.UUID
    zone_name: str
    camera_id: uuid.UUID
    track_id: int
    kind: ZoneTransitionKind
    occurred_at: datetime
    dwell_time_seconds: float | None = None


class ZoneOccupant(SentinelModel):
    """A track currently inside a zone, with its still-running dwell time."""

    track_id: int
    entered_at: datetime
    dwell_time_seconds: float
