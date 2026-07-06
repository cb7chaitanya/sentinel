"""Domain model for tracked warehouse entities (workers, forklifts, pallets, boxes).

An `Entity` is the memory service's durable identity for one (camera_id,
track_id) pair from the vision/tracking pipeline -- one row per object
ever seen, continuously updated in place as new observations arrive
(see `EntityObservation`), never duplicated.

There is deliberately no stored, mutable "is this entity still around"
flag: whether an entity counts as part of the *current* state is a pure
function of how recently it was last observed (see `is_active`), computed
at read time against an explicit reference time. That keeps "current
state" reproducible from the same data -- nothing to fall out of sync.
"""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum

from sentinel_common.schemas.common import TimestampedModel
from sentinel_common.schemas.detection import BoundingBox, Velocity
from sentinel_common.schemas.entity import EntityObservation

__all__ = [
    "DEFAULT_LABEL_ENTITY_TYPES",
    "EntityObservation",
    "EntityRead",
    "EntityType",
    "classify_entity_type",
]


class EntityType(StrEnum):
    WORKER = "worker"
    FORKLIFT = "forklift"
    PALLET = "pallet"
    BOX = "box"
    OTHER = "other"


# Deterministic, explicit label -> type lookup -- no inference, no model.
# Matches the stock COCO labels the vision service's default YOLO weights
# produce today; a warehouse-specific model would just need a different
# mapping, not different code (see Settings.label_entity_types).
DEFAULT_LABEL_ENTITY_TYPES: dict[str, EntityType] = {
    "person": EntityType.WORKER,
    "worker": EntityType.WORKER,
    "forklift": EntityType.FORKLIFT,
    "pallet": EntityType.PALLET,
    "box": EntityType.BOX,
}


def classify_entity_type(
    label: str, mapping: dict[str, EntityType] | None = None
) -> EntityType:
    """Deterministically bucket a raw detection label into an `EntityType`.

    Unrecognized labels map to `OTHER` rather than raising -- an unmapped
    label is expected (any model will eventually produce a class this
    mapping doesn't know about), not an error condition.
    """
    active_mapping = mapping if mapping is not None else DEFAULT_LABEL_ENTITY_TYPES
    return active_mapping.get(label.lower(), EntityType.OTHER)


class EntityRead(TimestampedModel):
    warehouse_id: uuid.UUID
    camera_id: uuid.UUID
    track_id: int
    entity_type: EntityType
    label: str
    bounding_box: BoundingBox
    velocity: Velocity | None = None
    first_seen_at: datetime
    last_seen_at: datetime

    def is_active(self, *, as_of: datetime, staleness_threshold_seconds: float) -> bool:
        """Whether this entity counts as part of the *current* state as of `as_of`."""
        return as_of - self.last_seen_at <= timedelta(seconds=staleness_threshold_seconds)
