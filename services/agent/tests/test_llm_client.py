import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from agent.domain.analysis import AnalysisContent, Citation, CitationKind, Insight
from agent.domain.context import AgentContext, EntitySnapshot, WarehouseStateSnapshot
from agent.infra.llm_client import AnthropicWarehouseAgent

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ENTITY_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _context() -> AgentContext:
    return AgentContext(
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
        )
    )


def _fake_client(content: AnalysisContent) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.parsed_output = content
    client.messages.parse = AsyncMock(return_value=response)
    return client


async def test_analyze_calls_the_model_with_system_prompt_and_rendered_context() -> None:
    content = AnalysisContent(insights=[])
    client = _fake_client(content)
    agent = AnthropicWarehouseAgent(client=client, model="claude-opus-4-8")

    await agent.analyze(_context())

    client.messages.parse.assert_awaited_once()
    _, kwargs = client.messages.parse.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_format"] is AnalysisContent
    assert str(WAREHOUSE_ID) in kwargs["messages"][0]["content"]
    assert "citation" in kwargs["system"].lower()


async def test_analyze_populates_envelope_fields_from_context_not_the_model() -> None:
    content = AnalysisContent(insights=[])
    client = _fake_client(content)
    agent = AnthropicWarehouseAgent(client=client, model="claude-opus-4-8")

    result = await agent.analyze(_context())

    assert result.warehouse_id == WAREHOUSE_ID
    assert result.generated_at == T0


async def test_analyze_applies_the_grounding_filter() -> None:
    ungrounded_insight = Insight(id="i1", summary="hallucinated", citations=[])
    grounded_insight = Insight(
        id="i2",
        summary="real",
        citations=[Citation(kind=CitationKind.ENTITY, reference_id=str(ENTITY_ID), detail="ok")],
    )
    content = AnalysisContent(insights=[ungrounded_insight, grounded_insight])
    client = _fake_client(content)
    agent = AnthropicWarehouseAgent(client=client, model="claude-opus-4-8")

    result = await agent.analyze(_context())

    assert [i.id for i in result.insights] == ["i2"]
