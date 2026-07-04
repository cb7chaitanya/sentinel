import uuid
from datetime import UTC, datetime

from agent.domain.analysis import (
    AgentAnalysis,
    Citation,
    CitationKind,
    Insight,
    PotentialIssue,
    Recommendation,
    Severity,
)
from agent.domain.context import (
    AgentContext,
    EntitySnapshot,
    InventoryRecord,
    SafetyRule,
    WarehouseStateSnapshot,
)
from agent.domain.copilot import CopilotAnswerContent
from agent.domain.evidence import AlertRecord, RetrievedEvidence
from agent.domain.grounding import filter_grounded, ground_copilot_answer
from sentinel_common.schemas.event import EventRead, EventType

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)

EVENT_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()
SKU = "PALLET-001"
RULE_ID = "dwell-001"


def _event() -> EventRead:
    return EventRead(
        id=EVENT_ID,
        created_at=T0,
        updated_at=T0,
        camera_id=CAMERA_ID,
        event_type=EventType.ZONE_ENTERED,
        occurred_at=T0,
        summary="Forklift entered Loading Dock",
    )


def _context(**overrides: object) -> AgentContext:
    defaults = dict(
        warehouse_state=WarehouseStateSnapshot(
            warehouse_id=WAREHOUSE_ID,
            generated_at=T0,
            entities=[
                EntitySnapshot(
                    entity_id=ENTITY_ID,
                    entity_type="forklift",
                    label="forklift",
                    camera_id=CAMERA_ID,
                    last_seen_at=T0,
                )
            ],
        ),
        recent_events=[_event()],
        inventory_records=[
            InventoryRecord(sku=SKU, description="Wooden pallet", expected_quantity=50)
        ],
        safety_rules=[
            SafetyRule(
                id=RULE_ID,
                description="No dwelling > 30 min in Loading Dock",
                severity="high",
            )
        ],
    )
    defaults.update(overrides)
    return AgentContext(**defaults)


def _analysis(
    *,
    insight_citations: list[Citation] | None = None,
    issue_citations: list[Citation] | None = None,
    recommendation_citations: list[Citation] | None = None,
) -> AgentAnalysis:
    valid_citation = Citation(kind=CitationKind.EVENT, reference_id=str(EVENT_ID), detail="test")
    return AgentAnalysis(
        warehouse_id=WAREHOUSE_ID,
        generated_at=T0,
        insights=[
            Insight(
                id="insight-1",
                summary="test insight",
                citations=insight_citations if insight_citations is not None else [valid_citation],
            )
        ],
        potential_issues=[
            PotentialIssue(
                id="issue-1",
                summary="test issue",
                severity=Severity.HIGH,
                citations=issue_citations if issue_citations is not None else [valid_citation],
            )
        ],
        recommendations=[
            Recommendation(
                id="rec-1",
                summary="test recommendation",
                rationale="because",
                citations=(
                    recommendation_citations
                    if recommendation_citations is not None
                    else [valid_citation]
                ),
            )
        ],
    )


def test_grounded_conclusions_survive_unchanged() -> None:
    context = _context()
    analysis = _analysis()

    result = filter_grounded(analysis, context)

    assert len(result.insights) == 1
    assert len(result.potential_issues) == 1
    assert len(result.recommendations) == 1


def test_conclusion_with_no_citations_is_dropped() -> None:
    context = _context()
    analysis = _analysis(insight_citations=[])

    result = filter_grounded(analysis, context)

    assert result.insights == []
    # Other conclusions are unaffected.
    assert len(result.potential_issues) == 1


def test_conclusion_citing_a_hallucinated_event_id_is_dropped() -> None:
    context = _context()
    fake_citation = Citation(
        kind=CitationKind.EVENT, reference_id=str(uuid.uuid4()), detail="made up"
    )
    analysis = _analysis(issue_citations=[fake_citation])

    result = filter_grounded(analysis, context)

    assert result.potential_issues == []


def test_conclusion_citing_a_real_entity_id_survives() -> None:
    context = _context()
    citation = Citation(
        kind=CitationKind.ENTITY, reference_id=str(ENTITY_ID), detail="the forklift"
    )
    analysis = _analysis(recommendation_citations=[citation])

    result = filter_grounded(analysis, context)

    assert len(result.recommendations) == 1


def test_conclusion_citing_a_real_inventory_sku_survives() -> None:
    context = _context()
    citation = Citation(kind=CitationKind.INVENTORY_RECORD, reference_id=SKU, detail="pallet stock")
    analysis = _analysis(recommendation_citations=[citation])

    result = filter_grounded(analysis, context)

    assert len(result.recommendations) == 1


def test_conclusion_citing_a_real_safety_rule_survives() -> None:
    context = _context()
    citation = Citation(kind=CitationKind.SAFETY_RULE, reference_id=RULE_ID, detail="dwell rule")
    analysis = _analysis(issue_citations=[citation])

    result = filter_grounded(analysis, context)

    assert len(result.potential_issues) == 1


def test_conclusion_citing_the_right_id_with_the_wrong_kind_is_dropped() -> None:
    context = _context()
    # This SKU is real, but the model tagged it as an event -- kind and id
    # must both match, since ids from different kinds could collide.
    wrong_kind_citation = Citation(kind=CitationKind.EVENT, reference_id=SKU, detail="mislabeled")
    analysis = _analysis(recommendation_citations=[wrong_kind_citation])

    result = filter_grounded(analysis, context)

    assert result.recommendations == []


def test_one_hallucinated_citation_among_several_drops_the_whole_conclusion() -> None:
    context = _context()
    real = Citation(kind=CitationKind.EVENT, reference_id=str(EVENT_ID), detail="real")
    fake = Citation(kind=CitationKind.ENTITY, reference_id=str(uuid.uuid4()), detail="fake")
    analysis = _analysis(insight_citations=[real, fake])

    result = filter_grounded(analysis, context)

    assert result.insights == []


def test_empty_context_drops_everything() -> None:
    context = AgentContext(
        warehouse_state=WarehouseStateSnapshot(warehouse_id=WAREHOUSE_ID, generated_at=T0)
    )
    analysis = _analysis()

    result = filter_grounded(analysis, context)

    assert result.insights == []
    assert result.potential_issues == []
    assert result.recommendations == []


def test_filter_grounded_preserves_envelope_fields() -> None:
    context = _context()
    analysis = _analysis()

    result = filter_grounded(analysis, context)

    assert result.warehouse_id == WAREHOUSE_ID
    assert result.generated_at == T0


def test_multiple_conclusions_are_filtered_independently() -> None:
    context = _context()
    valid = Citation(kind=CitationKind.EVENT, reference_id=str(EVENT_ID), detail="ok")
    invalid = Citation(kind=CitationKind.EVENT, reference_id="nonexistent", detail="bad")

    analysis = AgentAnalysis(
        warehouse_id=WAREHOUSE_ID,
        generated_at=T0,
        insights=[
            Insight(id="i1", summary="good", citations=[valid]),
            Insight(id="i2", summary="bad", citations=[invalid]),
        ],
    )

    result = filter_grounded(analysis, context)

    assert [i.id for i in result.insights] == ["i1"]


def _evidence() -> RetrievedEvidence:
    return RetrievedEvidence(
        entities=[
            EntitySnapshot(
                entity_id=ENTITY_ID,
                entity_type="forklift",
                label="forklift",
                camera_id=CAMERA_ID,
                last_seen_at=T0,
            )
        ],
        events=[_event()],
        alerts=[
            AlertRecord(
                id=uuid.uuid4(), severity="high", status="open", summary="test alert", created_at=T0
            )
        ],
    )


def test_ground_copilot_answer_returns_content_when_fully_grounded() -> None:
    evidence = _evidence()
    content = CopilotAnswerContent(
        answer="The forklift is real.",
        citations=[Citation(kind=CitationKind.ENTITY, reference_id=str(ENTITY_ID), detail="it")],
    )

    result = ground_copilot_answer(content, evidence)

    assert result is content


def test_ground_copilot_answer_returns_none_for_no_citations() -> None:
    content = CopilotAnswerContent(answer="Sure, it's over there.", citations=[])

    result = ground_copilot_answer(content, _evidence())

    assert result is None


def test_ground_copilot_answer_returns_none_for_hallucinated_citation() -> None:
    content = CopilotAnswerContent(
        answer="It's in Zone B.",
        citations=[Citation(kind=CitationKind.ENTITY, reference_id=str(uuid.uuid4()), detail="?")],
    )

    result = ground_copilot_answer(content, _evidence())

    assert result is None


def test_ground_copilot_answer_accepts_a_real_alert_citation() -> None:
    evidence = _evidence()
    alert_id = evidence.alerts[0].id
    content = CopilotAnswerContent(
        answer="It fired because of X.",
        citations=[
            Citation(kind=CitationKind.ALERT, reference_id=str(alert_id), detail="the alert")
        ],
    )

    result = ground_copilot_answer(content, evidence)

    assert result is content
