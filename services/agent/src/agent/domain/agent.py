"""Domain-level interface for a warehouse-reasoning agent.

`infra/llm_client.py` implements this Protocol against an LLM provider; the
API layer depends only on the abstraction so the underlying model/provider
can change without touching routes.
"""

from typing import Protocol

from sentinel_common.schemas.common import SentinelModel


class AgentQuery(SentinelModel):
    question: str
    camera_id: str | None = None


class AgentResponse(SentinelModel):
    answer: str


class WarehouseAgent(Protocol):
    async def ask(self, query: AgentQuery) -> AgentResponse: ...
