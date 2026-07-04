import uuid
from datetime import UTC, datetime

from agent.core.di import get_operations_copilot
from agent.domain.copilot import CopilotAnswer, CopilotQuestion
from agent.main import app
from fastapi.testclient import TestClient

WAREHOUSE_ID = uuid.uuid4()
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeCopilot:
    async def answer(self, question: CopilotQuestion) -> CopilotAnswer:
        return CopilotAnswer(
            question=question.question,
            warehouse_id=question.warehouse_id,
            generated_at=T0,
            answer="It's in Zone B.",
            citations=[],
            grounded=True,
        )


def test_ask_copilot_returns_the_answer() -> None:
    app.dependency_overrides[get_operations_copilot] = lambda: _FakeCopilot()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/copilot/ask",
            json={"warehouse_id": str(WAREHOUSE_ID), "question": "Where is the pallet?"},
        )
    finally:
        app.dependency_overrides.pop(get_operations_copilot, None)

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "It's in Zone B."
    assert body["grounded"] is True
