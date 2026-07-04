"""Domain model for warehouse alerts.

An `Alert` is distinct from an `Event`: events are an immutable, append-only
activity log (see `sentinel_common.schemas.event`); alerts are mutable
records with a lifecycle (open -> acknowledged -> resolved) that someone
needs to act on. An alert may reference the event that triggered it, but
memory itself does not decide which events warrant one -- that
classification is a rules concern for whatever calls `record_alert`, not
storage's job.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel, TimestampedModel


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertCreate(SentinelModel):
    warehouse_id: uuid.UUID
    camera_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    severity: AlertSeverity
    summary: str


class AlertRead(AlertCreate, TimestampedModel):
    status: AlertStatus = AlertStatus.OPEN
    resolved_at: datetime | None = None
