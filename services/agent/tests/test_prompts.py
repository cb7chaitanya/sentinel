import uuid
from datetime import UTC, datetime

from agent.domain.context import AgentContext, InventoryRecord, SafetyRule, WarehouseStateSnapshot
from agent.infra.prompts import render_analysis_prompt, system_prompt
from sentinel_common.schemas.event import EventRead, EventType

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_system_prompt_mentions_grounding_rules() -> None:
    text = system_prompt()

    assert "citation" in text.lower()
    assert "only" in text.lower()


def test_render_analysis_prompt_includes_warehouse_id_and_timestamp() -> None:
    context = AgentContext(
        warehouse_state=WarehouseStateSnapshot(warehouse_id=WAREHOUSE_ID, generated_at=T0)
    )

    rendered = render_analysis_prompt(context)

    assert str(WAREHOUSE_ID) in rendered
    assert T0.isoformat() in rendered


def test_render_analysis_prompt_embeds_events_inventory_and_rules() -> None:
    context = AgentContext(
        warehouse_state=WarehouseStateSnapshot(warehouse_id=WAREHOUSE_ID, generated_at=T0),
        recent_events=[
            EventRead(
                id=uuid.uuid4(),
                created_at=T0,
                updated_at=T0,
                camera_id=CAMERA_ID,
                event_type=EventType.OBJECT_MOVED,
                occurred_at=T0,
                summary="Pallet moved",
            )
        ],
        inventory_records=[
            InventoryRecord(sku="SKU-1", description="Widget", expected_quantity=10)
        ],
        safety_rules=[SafetyRule(id="rule-1", description="Wear a hard hat", severity="high")],
    )

    rendered = render_analysis_prompt(context)

    assert "Pallet moved" in rendered
    assert "SKU-1" in rendered
    assert "Wear a hard hat" in rendered


def test_render_analysis_prompt_handles_empty_context() -> None:
    context = AgentContext(
        warehouse_state=WarehouseStateSnapshot(warehouse_id=WAREHOUSE_ID, generated_at=T0)
    )

    rendered = render_analysis_prompt(context)

    assert "[]" in rendered
