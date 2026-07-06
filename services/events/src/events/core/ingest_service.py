"""Fans one tick of vision detections out into memory's write API.

`EventEngine.update()` already derives everything memory needs to know
about a tick: zone-entered/exited events carry every field required to
reconstruct the `ZoneTransition` memory's zone_occupancy table expects
(see `_zone_transition_from_event`), so this service never calls
`ZoneEngine.update()` a second time itself -- doing so would mutate the
zone engine's occupancy state twice for the same tick and silently drop
the transition on whichever call ran second.

Entity observations are recorded before anything else: memory's
zone-transition write requires an entity to already exist for that
(camera_id, track_id) (see `EntityNotFoundError` in the memory service),
so every tracked detection's observation is pushed and awaited first.
Events and zone-transitions have no such ordering constraint between each
other and are pushed concurrently.

`warehouse_id` is not on the wire from vision at all -- `Detection` only
knows camera/track/geometry (see `sentinel_common.schemas.detection`) --
so this service resolves it from `Settings.camera_warehouse_map`. Zone
events already carry it (each `Zone` names its own warehouse); motion
events (`OBJECT_MOVED`/`OBJECT_STOPPED`/`OBJECT_PICKED`) don't, and are
backfilled from the same map before being sent to memory, since an event
memory can't attribute to a warehouse is unreachable through any
warehouse-scoped read (`GET /events?warehouse_id=...`).

Every memory write is best-effort: one failed observation/event/zone-
transition is logged and skipped rather than aborting the whole tick or
propagating to the caller, since a single dropped write from an ingest
endpoint that runs once per frame is preferable to failing the request
vision is waiting on.
"""

import asyncio
import logging
import uuid

import httpx
from sentinel_common.schemas.detection import Detection, FrameDetections
from sentinel_common.schemas.entity import EntityObservation
from sentinel_common.schemas.event import EventCreate, EventType
from sentinel_common.schemas.zone import ZoneTransition, ZoneTransitionKind

from events.core.event_engine import EventEngine
from events.infra.memory_client import MemoryClient

logger = logging.getLogger(__name__)

_ZONE_EVENT_KINDS = {
    EventType.ZONE_ENTERED: ZoneTransitionKind.ENTERED,
    EventType.ZONE_EXITED: ZoneTransitionKind.EXITED,
}


def _zone_transition_from_event(event: EventCreate) -> ZoneTransition:
    """Reconstruct the `ZoneTransition` a zone-derived event was built from.

    `EventEngine._zone_events` copies every `ZoneTransition` field onto the
    `EventCreate` it emits, so this is a lossless reversal, not a guess.
    """
    assert event.warehouse_id is not None
    assert event.zone_id is not None
    assert event.zone_name is not None
    assert event.track_id is not None
    return ZoneTransition(
        warehouse_id=event.warehouse_id,
        zone_id=event.zone_id,
        zone_name=event.zone_name,
        camera_id=event.camera_id,
        track_id=event.track_id,
        kind=_ZONE_EVENT_KINDS[event.event_type],
        occurred_at=event.occurred_at,
        dwell_time_seconds=event.dwell_time_seconds,
    )


class DetectionIngestService:
    """Turns one tick of `FrameDetections` into memory writes."""

    def __init__(
        self,
        event_engine: EventEngine,
        memory: MemoryClient,
        *,
        camera_warehouse_map: dict[uuid.UUID, uuid.UUID],
    ) -> None:
        self._event_engine = event_engine
        self._memory = memory
        self._camera_warehouse_map = camera_warehouse_map

    async def ingest(self, frame_detections: FrameDetections) -> None:
        tracked = [d for d in frame_detections.detections if d.track_id is not None]
        await asyncio.gather(*(self._record_observation(d) for d in tracked))

        events = self._event_engine.update(
            frame_detections.timestamp, frame_detections.detections
        )
        stamped_events = [self._stamp_warehouse(event) for event in events]
        zone_transitions = [
            _zone_transition_from_event(event)
            for event in stamped_events
            if event.event_type in _ZONE_EVENT_KINDS
        ]

        await asyncio.gather(
            *(self._record_event(event) for event in stamped_events),
            *(self._record_zone_transition(transition) for transition in zone_transitions),
        )

    def _stamp_warehouse(self, event: EventCreate) -> EventCreate:
        if event.warehouse_id is not None:
            return event
        warehouse_id = self._camera_warehouse_map.get(event.camera_id)
        if warehouse_id is None:
            return event
        return event.model_copy(update={"warehouse_id": warehouse_id})

    async def _record_observation(self, detection: Detection) -> None:
        assert detection.track_id is not None
        warehouse_id = self._camera_warehouse_map.get(detection.camera_id)
        if warehouse_id is None:
            logger.warning(
                "no warehouse configured for camera %s; dropping observation for track %s",
                detection.camera_id,
                detection.track_id,
            )
            return
        observation = EntityObservation(
            warehouse_id=warehouse_id,
            camera_id=detection.camera_id,
            track_id=detection.track_id,
            label=detection.label,
            bounding_box=detection.bounding_box,
            velocity=detection.velocity,
            observed_at=detection.captured_at,
        )
        try:
            await self._memory.record_observation(observation)
        except httpx.HTTPError:
            logger.warning(
                "failed to record observation for camera %s track %s",
                detection.camera_id,
                detection.track_id,
                exc_info=True,
            )

    async def _record_event(self, event: EventCreate) -> None:
        try:
            await self._memory.record_event(event)
        except httpx.HTTPError:
            logger.warning("failed to record event %s", event.event_type, exc_info=True)

    async def _record_zone_transition(self, transition: ZoneTransition) -> None:
        try:
            await self._memory.record_zone_transition(transition)
        except httpx.HTTPError:
            logger.warning(
                "failed to record zone transition for zone %s track %s",
                transition.zone_id,
                transition.track_id,
                exc_info=True,
            )
