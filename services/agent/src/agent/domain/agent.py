"""Domain-level interface for the AI warehouse-reasoning agent.

`infra/llm_client.py` implements this Protocol against Anthropic; callers
depend only on this abstraction, so the underlying model/provider can
change without touching them. The contract is fixed regardless of
provider: given an `AgentContext`, produce a grounded `AgentAnalysis` --
never inventing a fact beyond what the context contains (see
`domain/grounding.py` for how "grounded" is actually enforced, not just
requested by the prompt).
"""

from typing import Protocol

from agent.domain.analysis import AgentAnalysis
from agent.domain.context import AgentContext


class WarehouseAgent(Protocol):
    async def analyze(self, context: AgentContext) -> AgentAnalysis: ...
