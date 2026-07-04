"""Polygon-based implementation of `domain.zone_engine.ZoneEngine`.

Occupancy uses a grace period rather than flipping to "exited" the instant
a track isn't reconfirmed inside a zone: a single missed detection
(occlusion, a dropped frame, a momentary tracking glitch) shouldn't
register as a real zone exit. A track is only finalized as exited once
it's gone unconfirmed for `exit_grace_period_seconds` -- which also
correctly handles an object leaving the camera's view entirely, since that
too just looks like "no longer reconfirmed." Dwell time is measured up to
the last tick the object was actually confirmed inside, not including that
grace window, so it isn't inflated by absence.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sentinel_common.schemas.detection import BoundingBox, Detection
from sentinel_common.schemas.zone import ZoneOccupant, ZoneTransition, ZoneTransitionKind

from events.domain.zone import Point, Zone


def _anchor_point(bounding_box: BoundingBox) -> Point:
    """The ground point a bounding box represents, for zone membership.

    Bottom-center ("feet" position) rather than the box center: for a
    person or forklift, the box center is roughly chest/mid-body height --
    a worse proxy for "where they are standing on the floor" than the
    bottom edge.
    """
    return Point(x=(bounding_box.x_min + bounding_box.x_max) / 2.0, y=bounding_box.y_max)


@dataclass
class _Occupancy:
    entered_at: datetime
    last_confirmed_at: datetime


def _dwell_time_seconds(occupancy: _Occupancy) -> float:
    return (occupancy.last_confirmed_at - occupancy.entered_at).total_seconds()


class PolygonZoneEngine:
    def __init__(self, zones: list[Zone], *, exit_grace_period_seconds: float = 0.0) -> None:
        self._zones_by_id: dict[uuid.UUID, Zone] = {zone.id: zone for zone in zones}
        self._zones_by_camera: dict[uuid.UUID, list[Zone]] = defaultdict(list)
        for zone in zones:
            self._zones_by_camera[zone.camera_id].append(zone)
        self._exit_grace_period_seconds = exit_grace_period_seconds
        self._occupancy: dict[tuple[uuid.UUID, int], _Occupancy] = {}

    def update(self, timestamp: datetime, detections: list[Detection]) -> list[ZoneTransition]:
        transitions: list[ZoneTransition] = []
        confirmed_this_tick: set[tuple[uuid.UUID, int]] = set()

        detections_by_camera: dict[uuid.UUID, list[Detection]] = defaultdict(list)
        for detection in detections:
            if detection.track_id is not None:
                detections_by_camera[detection.camera_id].append(detection)

        for camera_id, camera_detections in detections_by_camera.items():
            zones = self._zones_by_camera.get(camera_id)
            if not zones:
                continue
            for zone in zones:
                for detection in camera_detections:
                    track_id = detection.track_id
                    if track_id is None or not zone.polygon.contains(
                        _anchor_point(detection.bounding_box)
                    ):
                        continue

                    key = (zone.id, track_id)
                    confirmed_this_tick.add(key)
                    occupancy = self._occupancy.get(key)
                    if occupancy is None:
                        self._occupancy[key] = _Occupancy(
                            entered_at=timestamp, last_confirmed_at=timestamp
                        )
                        transitions.append(
                            ZoneTransition(
                                warehouse_id=zone.warehouse_id,
                                zone_id=zone.id,
                                zone_name=zone.name,
                                camera_id=zone.camera_id,
                                track_id=track_id,
                                kind=ZoneTransitionKind.ENTERED,
                                occurred_at=timestamp,
                            )
                        )
                    else:
                        occupancy.last_confirmed_at = timestamp

        for key, occupancy in list(self._occupancy.items()):
            if key in confirmed_this_tick:
                continue
            elapsed_since_confirmed = (timestamp - occupancy.last_confirmed_at).total_seconds()
            if elapsed_since_confirmed < self._exit_grace_period_seconds:
                continue

            zone_id, track_id = key
            zone = self._zones_by_id[zone_id]
            dwell_time_seconds = _dwell_time_seconds(occupancy)
            transitions.append(
                ZoneTransition(
                    warehouse_id=zone.warehouse_id,
                    zone_id=zone.id,
                    zone_name=zone.name,
                    camera_id=zone.camera_id,
                    track_id=track_id,
                    kind=ZoneTransitionKind.EXITED,
                    occurred_at=timestamp,
                    dwell_time_seconds=dwell_time_seconds,
                )
            )
            del self._occupancy[key]

        return transitions

    def current_occupants(self, zone_id: uuid.UUID) -> list[ZoneOccupant]:
        occupants: list[ZoneOccupant] = []
        for (zid, track_id), occupancy in self._occupancy.items():
            if zid != zone_id:
                continue
            occupants.append(
                ZoneOccupant(
                    track_id=track_id,
                    entered_at=occupancy.entered_at,
                    dwell_time_seconds=_dwell_time_seconds(occupancy),
                )
            )
        return occupants

    def zones(self, warehouse_id: uuid.UUID | None = None) -> list[Zone]:
        if warehouse_id is None:
            return list(self._zones_by_id.values())
        return [zone for zone in self._zones_by_id.values() if zone.warehouse_id == warehouse_id]
