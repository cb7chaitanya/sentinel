"""Schema for one tick's sighting of a tracked object.

`EntityObservation` is the boundary artifact producers (today: the events
service, deriving it from vision's `Detection`s) send to the memory
service's `POST /observations` -- the same role `ZoneTransition` and
`EventCreate` play for zone occupancy and the event stream. It lives here
rather than only in `memory.domain.entity` because it's a cross-service
wire format, not a memory-service-internal concept.
"""

import uuid
from datetime import datetime

from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.detection import BoundingBox, Velocity


class EntityObservation(SentinelModel):
    """One tick's sighting of a tracked object, as recorded into memory.

    Deliberately not `sentinel_common.Detection`: memory additionally needs
    a `warehouse_id` (detections have no notion of warehouse) and has no
    use for detector confidence (a detection-quality signal, not a state
    one). `entity_type` is derived from `label` by the repository via
    `classify_entity_type`, not supplied by the caller -- classification
    stays centralized and consistent in one place.
    """

    warehouse_id: uuid.UUID
    camera_id: uuid.UUID
    track_id: int
    label: str
    bounding_box: BoundingBox
    velocity: Velocity | None = None
    observed_at: datetime
