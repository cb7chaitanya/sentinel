"""Domain model for zone occupancy intervals.

One row covers one continuous stay in a zone: `exited_at` is `None` while
the entity is still inside, and set once it leaves -- the same interval
row serves as both "who's in this zone right now" (`exited_at IS NULL`)
and the historical record (every row, open or closed), so there is no
separate "current" table to keep in sync with a "history" table.
"""

import uuid
from datetime import datetime

from sentinel_common.schemas.common import TimestampedModel


class ZoneOccupancyRead(TimestampedModel):
    warehouse_id: uuid.UUID
    zone_id: uuid.UUID
    zone_name: str
    entity_id: uuid.UUID
    entered_at: datetime
    exited_at: datetime | None = None

    def dwell_time_seconds(self, *, as_of: datetime | None = None) -> float:
        """Time spent in the zone so far (or in total, once exited).

        `as_of` is only used while still inside (`exited_at is None`); it's
        ignored for a closed interval, which already has a fixed duration.
        """
        end = self.exited_at or as_of or self.entered_at
        return (end - self.entered_at).total_seconds()
