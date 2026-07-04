import uuid
from datetime import UTC, datetime

from agent.domain.context import EntitySnapshot
from agent.domain.evidence import AlertRecord, RetrievedEvidence, merge_evidence
from sentinel_common.schemas.event import EventRead, EventType

CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _entity() -> EntitySnapshot:
    return EntitySnapshot(
        entity_id=uuid.uuid4(),
        entity_type="pallet",
        label="pallet",
        camera_id=CAMERA_ID,
        last_seen_at=T0,
    )


def _event() -> EventRead:
    return EventRead(
        id=uuid.uuid4(),
        created_at=T0,
        updated_at=T0,
        camera_id=CAMERA_ID,
        event_type=EventType.ZONE_ENTERED,
        occurred_at=T0,
        summary="test event",
    )


def _alert() -> AlertRecord:
    return AlertRecord(
        id=uuid.uuid4(), severity="high", status="open", summary="test alert", created_at=T0
    )


def test_merge_unions_disjoint_bundles() -> None:
    entity, event, alert = _entity(), _event(), _alert()
    a = RetrievedEvidence(entities=[entity])
    b = RetrievedEvidence(events=[event], alerts=[alert])

    result = merge_evidence(a, b)

    assert result.entities == [entity]
    assert result.events == [event]
    assert result.alerts == [alert]


def test_merge_deduplicates_by_id() -> None:
    entity = _entity()
    a = RetrievedEvidence(entities=[entity])
    b = RetrievedEvidence(entities=[entity])

    result = merge_evidence(a, b)

    assert len(result.entities) == 1


def test_merge_with_no_bundles_is_empty() -> None:
    result = merge_evidence()

    assert result.is_empty()


def test_is_empty_false_when_anything_present() -> None:
    assert not RetrievedEvidence(entities=[_entity()]).is_empty()
    assert not RetrievedEvidence(events=[_event()]).is_empty()
    assert not RetrievedEvidence(alerts=[_alert()]).is_empty()


def test_is_empty_true_for_a_blank_bundle() -> None:
    assert RetrievedEvidence().is_empty()
