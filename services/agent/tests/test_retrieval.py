import uuid
from datetime import UTC, datetime

from agent.domain.context import EntitySnapshot, ZoneMembership
from agent.domain.copilot import CopilotQuestion
from agent.domain.evidence import AlertRecord, RetrievedEvidence
from agent.domain.retrieval import retrieve_evidence
from sentinel_common.schemas.event import EventRead, EventType

CAMERA_ID = uuid.uuid4()
WAREHOUSE_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _entity(
    *, entity_type: str, label: str, zones: list[ZoneMembership] | None = None
) -> EntitySnapshot:
    return EntitySnapshot(
        entity_id=uuid.uuid4(),
        entity_type=entity_type,
        label=label,
        camera_id=CAMERA_ID,
        last_seen_at=T0,
        current_zones=zones or [],
    )


def _event(*, zone_name: str | None) -> EventRead:
    return EventRead(
        id=uuid.uuid4(),
        created_at=T0,
        updated_at=T0,
        camera_id=CAMERA_ID,
        event_type=EventType.ZONE_ENTERED,
        occurred_at=T0,
        summary="test event",
        zone_name=zone_name,
    )


def _alert() -> AlertRecord:
    return AlertRecord(
        id=uuid.uuid4(), severity="high", status="open", summary="test alert", created_at=T0
    )


def _question(text: str, **hints: object) -> CopilotQuestion:
    return CopilotQuestion(warehouse_id=WAREHOUSE_ID, question=text, **hints)


def test_entity_id_hint_narrows_to_exactly_that_entity() -> None:
    target = _entity(entity_type="pallet", label="pallet")
    other = _entity(entity_type="pallet", label="pallet")
    pool = RetrievedEvidence(entities=[target, other])

    result = retrieve_evidence(_question("where is it?", entity_id=target.entity_id), pool)

    assert [e.entity_id for e in result.entities] == [target.entity_id]


def test_entity_type_keyword_narrows_to_matching_type() -> None:
    pallet = _entity(entity_type="pallet", label="pallet")
    forklift = _entity(entity_type="forklift", label="forklift")
    pool = RetrievedEvidence(entities=[pallet, forklift])

    result = retrieve_evidence(_question("where are the pallets?"), pool)

    assert [e.entity_id for e in result.entities] == [pallet.entity_id]


def test_code_token_matches_entity_label() -> None:
    # Deliberately omits the word "pallet" itself, to isolate the code-matching
    # path from the entity-type-keyword path tested separately above -- when
    # both a type and a code are mentioned (as in "pallet P103"), matches are
    # a union: everything of that type, plus anything matching the code.
    p103 = _entity(entity_type="pallet", label="P103")
    other = _entity(entity_type="pallet", label="P204")
    pool = RetrievedEvidence(entities=[p103, other])

    result = retrieve_evidence(_question("Where is P103?"), pool)

    assert [e.entity_id for e in result.entities] == [p103.entity_id]


def test_zone_name_hint_filters_events_by_zone() -> None:
    zone_b_event = _event(zone_name="Zone B")
    zone_a_event = _event(zone_name="Zone A")
    pool = RetrievedEvidence(events=[zone_b_event, zone_a_event])

    result = retrieve_evidence(_question("what happened?", zone_name="Zone B"), pool)

    assert [e.id for e in result.events] == [zone_b_event.id]


def test_zone_name_mentioned_in_free_text_filters_events() -> None:
    zone_b_event = _event(zone_name="Zone B")
    zone_a_event = _event(zone_name="Zone A")
    pool = RetrievedEvidence(events=[zone_b_event, zone_a_event])

    result = retrieve_evidence(_question("What happened in Zone B?"), pool)

    assert [e.id for e in result.events] == [zone_b_event.id]


def test_zone_mention_also_narrows_entities_by_current_zone() -> None:
    in_zone_b = _entity(
        entity_type="forklift",
        label="forklift",
        zones=[ZoneMembership(zone_name="Zone B", dwell_time_seconds=10)],
    )
    in_zone_a = _entity(
        entity_type="forklift",
        label="forklift",
        zones=[ZoneMembership(zone_name="Zone A", dwell_time_seconds=10)],
    )
    pool = RetrievedEvidence(
        entities=[in_zone_b, in_zone_a], events=[_event(zone_name="Zone B")]
    )

    result = retrieve_evidence(_question("What happened in Zone B?"), pool)

    assert [e.entity_id for e in result.entities] == [in_zone_b.entity_id]


def test_alert_id_hint_narrows_to_exactly_that_alert() -> None:
    target = _alert()
    other = _alert()
    pool = RetrievedEvidence(alerts=[target, other])

    result = retrieve_evidence(_question("why did this fire?", alert_id=target.id), pool)

    assert [a.id for a in result.alerts] == [target.id]


def test_no_signal_at_all_passes_everything_through() -> None:
    pool = RetrievedEvidence(
        entities=[_entity(entity_type="worker", label="worker")],
        events=[_event(zone_name="Zone A")],
        alerts=[_alert()],
    )

    result = retrieve_evidence(_question("what's going on?"), pool)

    assert len(result.entities) == 1
    assert len(result.events) == 1
    assert len(result.alerts) == 1
