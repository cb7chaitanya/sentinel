import uuid
from datetime import UTC, datetime

import httpx
from events.core.event_engine import EventEngine
from events.core.ingest_service import DetectionIngestService
from events.domain.zone import Point, Polygon, Zone
from events.infra.polygon_zone_engine import PolygonZoneEngine
from sentinel_common.schemas.detection import BoundingBox, Detection, FrameDetections
from sentinel_common.schemas.entity import EntityObservation
from sentinel_common.schemas.event import EventCreate, EventType
from sentinel_common.schemas.zone import ZoneTransition

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
UNMAPPED_CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class FakeMemoryClient:
    def __init__(self, *, fail_track_ids: set[int] | None = None) -> None:
        self.observations: list[EntityObservation] = []
        self.zone_transitions: list[ZoneTransition] = []
        self.events: list[EventCreate] = []
        self._fail_track_ids = fail_track_ids or set()

    async def record_observation(self, observation: EntityObservation) -> None:
        if observation.track_id in self._fail_track_ids:
            raise httpx.ConnectError("boom")
        self.observations.append(observation)

    async def record_zone_transition(self, transition: ZoneTransition) -> None:
        self.zone_transitions.append(transition)

    async def record_event(self, event: EventCreate) -> None:
        self.events.append(event)


def _dock_zone() -> Zone:
    return Zone(
        id=uuid.uuid4(),
        warehouse_id=WAREHOUSE_ID,
        camera_id=CAMERA_ID,
        name="Loading Dock",
        polygon=Polygon(
            points=[
                Point(x=0, y=0),
                Point(x=1000, y=0),
                Point(x=1000, y=1000),
                Point(x=0, y=1000),
            ]
        ),
    )


def _detection(
    *, camera_id: uuid.UUID = CAMERA_ID, track_id: int | None = 1, label: str = "forklift"
) -> Detection:
    return Detection(
        camera_id=camera_id,
        captured_at=T0,
        label=label,
        confidence=0.9,
        bounding_box=BoundingBox(x_min=10, y_min=10, x_max=20, y_max=20),
        track_id=track_id,
    )


def _service(
    memory: FakeMemoryClient, *, zones: list[Zone] | None = None
) -> DetectionIngestService:
    zone_engine = PolygonZoneEngine(zones if zones is not None else [_dock_zone()])
    event_engine = EventEngine(zone_engine)
    return DetectionIngestService(
        event_engine, memory, camera_warehouse_map={CAMERA_ID: WAREHOUSE_ID}
    )


async def test_ingest_records_an_observation_for_every_tracked_detection() -> None:
    memory = FakeMemoryClient()
    service = _service(memory)

    await service.ingest(
        FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[_detection(track_id=1)])
    )

    assert len(memory.observations) == 1
    observation = memory.observations[0]
    assert observation.warehouse_id == WAREHOUSE_ID
    assert observation.camera_id == CAMERA_ID
    assert observation.track_id == 1


async def test_ingest_skips_observations_for_untracked_detections() -> None:
    memory = FakeMemoryClient()
    service = _service(memory)

    await service.ingest(
        FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[_detection(track_id=None)])
    )

    assert memory.observations == []


async def test_ingest_skips_observations_for_unmapped_cameras() -> None:
    memory = FakeMemoryClient()
    service = _service(memory, zones=[])

    await service.ingest(
        FrameDetections(
            camera_id=UNMAPPED_CAMERA_ID,
            timestamp=T0,
            detections=[_detection(camera_id=UNMAPPED_CAMERA_ID, track_id=1)],
        )
    )

    assert memory.observations == []


async def test_ingest_records_a_zone_entered_event_and_its_zone_transition() -> None:
    memory = FakeMemoryClient()
    service = _service(memory)

    await service.ingest(
        FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[_detection(track_id=1)])
    )

    assert len(memory.events) == 1
    event = memory.events[0]
    assert event.event_type is EventType.ZONE_ENTERED
    assert event.warehouse_id == WAREHOUSE_ID

    assert len(memory.zone_transitions) == 1
    transition = memory.zone_transitions[0]
    assert transition.warehouse_id == WAREHOUSE_ID
    assert transition.zone_name == "Loading Dock"
    assert transition.track_id == 1


async def test_ingest_backfills_warehouse_id_onto_motion_events() -> None:
    memory = FakeMemoryClient()
    service = _service(memory, zones=[])

    await service.ingest(
        FrameDetections(
            camera_id=CAMERA_ID, timestamp=T0, detections=[_detection(label="pallet", track_id=1)]
        )
    )
    # Second tick with motion so the pallet transitions to "moving".
    from sentinel_common.schemas.detection import Velocity

    moving = _detection(label="pallet", track_id=1)
    moving = moving.model_copy(update={"velocity": Velocity(vx=10.0, vy=0.0)})
    await service.ingest(
        FrameDetections(camera_id=CAMERA_ID, timestamp=T0, detections=[moving])
    )

    moved_events = [e for e in memory.events if e.event_type is EventType.OBJECT_MOVED]
    assert len(moved_events) == 1
    assert moved_events[0].warehouse_id == WAREHOUSE_ID
    # Motion events never carry zone fields, so they must never be
    # reconstructed into a (bogus) zone transition.
    assert memory.zone_transitions == []


async def test_a_failed_observation_does_not_prevent_other_writes() -> None:
    memory = FakeMemoryClient(fail_track_ids={1})
    service = _service(memory)

    await service.ingest(
        FrameDetections(
            camera_id=CAMERA_ID,
            timestamp=T0,
            detections=[_detection(track_id=1), _detection(track_id=2, label="pallet")],
        )
    )

    assert [o.track_id for o in memory.observations] == [2]
    # Both tracks still produced their zone_entered event/transition -- a
    # dropped observation degrades gracefully rather than aborting the tick.
    assert len(memory.events) == 2
