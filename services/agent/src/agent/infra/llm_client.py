"""Anthropic-backed implementation of `domain.agent.WarehouseAgent`.

Stubbed out: prompt construction, memory-service retrieval, and tool use
are follow-up work.
"""

from anthropic import AsyncAnthropic

from agent.domain.agent import AgentQuery, AgentResponse, WarehouseAgent


class AnthropicWarehouseAgent(WarehouseAgent):
    def __init__(self, client: AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def ask(self, query: AgentQuery) -> AgentResponse:
        raise NotImplementedError
