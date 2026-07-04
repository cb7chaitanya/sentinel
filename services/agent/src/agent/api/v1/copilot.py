from fastapi import APIRouter

from agent.core.di import OperationsCopilotDep
from agent.domain.copilot import CopilotAnswer, CopilotQuestion

router = APIRouter()


@router.post("/copilot/ask", response_model=CopilotAnswer)
async def ask_copilot(
    question: CopilotQuestion, copilot: OperationsCopilotDep
) -> CopilotAnswer:
    return await copilot.answer(question)
