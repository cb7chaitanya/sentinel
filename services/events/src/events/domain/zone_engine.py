"""Domain-level interface for tracking zone occupancy over time.

`infra/polygon_zone_engine.py` implements this Protocol using polygon
point-in-polygon tests; callers depend only on this abstraction, so the
membership test (e.g. real-world coordinates after camera calibration,
instead of raw pixel space) could change without touching them.
"""

import uuid
from datetime import datetime
from typing import Protocol

from sentinel_common.schemas.detection import Detection
from sentinel_common.schemas.zone import ZoneOccupant, ZoneTransition

from events.domain.zone import Zone


class ZoneEngine(Protocol):
    """Tracks occupancy for every configured zone, across warehouses/cameras.

    A single instance handles all configured zones: each `Zone` already
    carries its own `warehouse_id`/`camera_id`, so state for different
    warehouses never mixes as long as zone ids are unique.
    """

    def update(self, timestamp: datetime, detections: list[Detection]) -> list[ZoneTransition]:
        """Update zone membership from one tick of tracked detections.

        Returns any ENTERED/EXITED transitions that occurred this tick.
        Detections with no `track_id` are ignored -- zone occupancy is only
        meaningful for tracked objects.
        """
        ...

    def current_occupants(self, zone_id: uuid.UUID) -> list[ZoneOccupant]:
        """Tracks currently inside `zone_id`, with their running dwell time."""
        ...

    def zones(self, warehouse_id: uuid.UUID | None = None) -> list[Zone]:
        """All configured zones, optionally filtered to one warehouse."""
        ...
