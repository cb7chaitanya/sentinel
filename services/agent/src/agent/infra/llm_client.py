"""Anthropic-backed implementation of `domain.agent.WarehouseAgent`.

Uses structured outputs (`messages.parse` with `output_format`) so the
response is guaranteed to match `AnalysisContent`'s shape -- no "please
respond with JSON" in the prompt, no manual `json.loads`. That guarantees
*shape*, not *truth*: nothing stops the model from citing an id it made
up, so every response still goes through `domain.grounding.filter_grounded`
before it's returned. That check, not the prompt, is what "never invent
facts" actually rests on.

`warehouse_id`/`generated_at` are not asked of the model at all -- they're
known for certain from `context`, so there's nothing for the model to get
right or wrong about them.
"""

from anthropic import AsyncAnthropic

from agent.domain.agent import WarehouseAgent
from agent.domain.analysis import AgentAnalysis, AnalysisContent
from agent.domain.context import AgentContext
from agent.domain.grounding import filter_grounded
from agent.infra.prompts import render_analysis_prompt, system_prompt


class AnthropicWarehouseAgent(WarehouseAgent):
    def __init__(self, client: AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def analyze(self, context: AgentContext) -> AgentAnalysis:
        response = await self._client.messages.parse(
            model=self._model,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=system_prompt(),
            messages=[{"role": "user", "content": render_analysis_prompt(context)}],
            output_format=AnalysisContent,
        )
        content = response.parsed_output

        analysis = AgentAnalysis(
            warehouse_id=context.warehouse_state.warehouse_id,
            generated_at=context.warehouse_state.generated_at,
            insights=content.insights,
            potential_issues=content.potential_issues,
            recommendations=content.recommendations,
        )
        return filter_grounded(analysis, context)
