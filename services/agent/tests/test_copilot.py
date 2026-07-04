import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from agent.domain.citation import Citation, CitationKind
from agent.domain.context import EntitySnapshot
from agent.domain.copilot import (
    NO_EVIDENCE_ANSWER,
    UNGROUNDED_ANSWER_FALLBACK,
    CopilotAnswerContent,
    CopilotQuestion,
)
from agent.domain.evidence import AlertRecord, RetrievedEvidence
from agent.infra.copilot import MemoryBackedCopilot
from sentinel_common.schemas.event import EventRead, EventType

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()
ALERT_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _entity() -> EntitySnapshot:
    return EntitySnapshot(
        entity_id=ENTITY_ID,
        entity_type="pallet",
        label="pallet",
        camera_id=CAMERA_ID,
        last_seen_at=T0,
    )


def _event() -> EventRead:
    return EventRead(
        id=EVENT_ID,
        created_at=T0,
        updated_at=T0,
        camera_id=CAMERA_ID,
        event_type=EventType.ZONE_ENTERED,
        occurred_at=T0,
        summary="Pallet entered Zone B",
        zone_name="Zone B",
    )


def _alert() -> AlertRecord:
    return AlertRecord(
        id=ALERT_ID, severity="high", status="open", summary="test alert", created_at=T0
    )


def _memory(
    *,
    snapshot: RetrievedEvidence | None = None,
    entity_history: tuple | None = None,
    alert: AlertRecord | None = None,
    event: EventRead | None = None,
) -> MagicMock:
    memory = MagicMock()
    memory.get_current_snapshot = AsyncMock(return_value=snapshot or RetrievedEvidence())
    memory.get_entity_history = AsyncMock(return_value=entity_history)
    memory.get_alert = AsyncMock(return_value=alert)
    memory.get_event = AsyncMock(return_value=event)
    return memory


def _llm(content: CopilotAnswerContent) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.parsed_output = content
    client.messages.parse = AsyncMock(return_value=response)
    return client


def _question(**overrides: object) -> CopilotQuestion:
    defaults = dict(warehouse_id=WAREHOUSE_ID, question="Where is the pallet?")
    defaults.update(overrides)
    return CopilotQuestion(**defaults)


async def test_no_evidence_short_circuits_without_calling_the_llm() -> None:
    memory = _memory(snapshot=RetrievedEvidence())
    llm = _llm(CopilotAnswerContent(answer="irrelevant", citations=[]))
    copilot = MemoryBackedCopilot(memory=memory, llm=llm, model="claude-opus-4-8")

    result = await copilot.answer(_question())

    llm.messages.parse.assert_not_awaited()
    assert result.grounded is False
    assert result.answer == NO_EVIDENCE_ANSWER
    assert result.citations == []


async def test_grounded_answer_is_returned_as_is() -> None:
    memory = _memory(snapshot=RetrievedEvidence(entities=[_entity()]))
    content = CopilotAnswerContent(
        answer="It's in Zone B.",
        citations=[Citation(kind=CitationKind.ENTITY, reference_id=str(ENTITY_ID), detail="it")],
    )
    llm = _llm(content)
    copilot = MemoryBackedCopilot(memory=memory, llm=llm, model="claude-opus-4-8")

    result = await copilot.answer(_question())

    assert result.grounded is True
    assert result.answer == "It's in Zone B."
    assert len(result.citations) == 1
    assert result.warehouse_id == WAREHOUSE_ID


async def test_ungrounded_answer_is_replaced_with_fallback() -> None:
    memory = _memory(snapshot=RetrievedEvidence(entities=[_entity()]))
    content = CopilotAnswerContent(
        answer="It's definitely in Zone Q.",
        citations=[Citation(kind=CitationKind.ENTITY, reference_id=str(uuid.uuid4()), detail="?")],
    )
    llm = _llm(content)
    copilot = MemoryBackedCopilot(memory=memory, llm=llm, model="claude-opus-4-8")

    result = await copilot.answer(_question())

    assert result.grounded is False
    assert result.answer == UNGROUNDED_ANSWER_FALLBACK


async def test_entity_id_hint_fetches_and_merges_entity_history() -> None:
    memory = _memory(
        snapshot=RetrievedEvidence(),
        entity_history=(_entity(), [_event()]),
    )
    content = CopilotAnswerContent(
        answer="It's in Zone B.",
        citations=[Citation(kind=CitationKind.EVENT, reference_id=str(EVENT_ID), detail="it")],
    )
    llm = _llm(content)
    copilot = MemoryBackedCopilot(memory=memory, llm=llm, model="claude-opus-4-8")

    result = await copilot.answer(_question(entity_id=ENTITY_ID))

    memory.get_entity_history.assert_awaited_once_with(ENTITY_ID)
    assert result.grounded is True


async def test_alert_id_hint_fetches_alert_and_its_triggering_event() -> None:
    memory = _memory(
        snapshot=RetrievedEvidence(),
        alert=AlertRecord(
            id=ALERT_ID,
            severity="high",
            status="open",
            summary="Dwell exceeded",
            event_id=EVENT_ID,
            created_at=T0,
        ),
        event=_event(),
    )
    content = CopilotAnswerContent(
        answer="It fired because of a dwell-time breach.",
        citations=[Citation(kind=CitationKind.ALERT, reference_id=str(ALERT_ID), detail="it")],
    )
    llm = _llm(content)
    copilot = MemoryBackedCopilot(memory=memory, llm=llm, model="claude-opus-4-8")

    result = await copilot.answer(
        _question(question="Why was this alert generated?", alert_id=ALERT_ID)
    )

    memory.get_alert.assert_awaited_once_with(ALERT_ID)
    memory.get_event.assert_awaited_once_with(EVENT_ID)
    assert result.grounded is True
