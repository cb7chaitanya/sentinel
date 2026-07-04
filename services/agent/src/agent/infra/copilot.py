"""`MemoryBackedCopilot`: retrieval from memory, generation from Anthropic.

Ordering is the whole point, not an implementation detail: retrieval runs
to completion, entirely independent of the LLM, before generation is even
considered. If it turns up nothing, the LLM is never called -- there is
nothing for it to ground an answer in, so calling it could only produce
an unsupported guess. Only once real evidence exists does generation run,
and even then its answer is checked against that same evidence
(`domain.grounding.ground_copilot_answer`) before being returned.
"""

from datetime import UTC, datetime

from anthropic import AsyncAnthropic

from agent.domain.citation import Citation
from agent.domain.copilot import (
    NO_EVIDENCE_ANSWER,
    UNGROUNDED_ANSWER_FALLBACK,
    CopilotAnswer,
    CopilotAnswerContent,
    CopilotQuestion,
)
from agent.domain.evidence import RetrievedEvidence, merge_evidence
from agent.domain.grounding import ground_copilot_answer
from agent.domain.retrieval import retrieve_evidence
from agent.infra.memory_client import MemoryClient
from agent.infra.prompts import copilot_system_prompt, render_copilot_prompt


class MemoryBackedCopilot:
    def __init__(self, memory: MemoryClient, llm: AsyncAnthropic, model: str) -> None:
        self._memory = memory
        self._llm = llm
        self._model = model

    async def answer(self, question: CopilotQuestion) -> CopilotAnswer:
        pool = await self._fetch_pool(question)
        evidence = retrieve_evidence(question, pool)
        generated_at = datetime.now(UTC)

        if evidence.is_empty():
            return self._answer(question, generated_at, NO_EVIDENCE_ANSWER, [], grounded=False)

        response = await self._llm.messages.parse(
            model=self._model,
            max_tokens=4000,
            thinking={"type": "adaptive"},
            system=copilot_system_prompt(),
            messages=[{"role": "user", "content": render_copilot_prompt(question, evidence)}],
            output_format=CopilotAnswerContent,
        )
        grounded = ground_copilot_answer(response.parsed_output, evidence)

        if grounded is None:
            return self._answer(
                question, generated_at, UNGROUNDED_ANSWER_FALLBACK, [], grounded=False
            )
        return self._answer(
            question, generated_at, grounded.answer, grounded.citations, grounded=True
        )

    async def _fetch_pool(self, question: CopilotQuestion) -> RetrievedEvidence:
        """Everything worth considering for `question`: the current snapshot,
        plus whatever any explicit hint (`entity_id`/`alert_id`) points at
        directly -- history endpoints memory can answer exactly, not by
        keyword guesswork.
        """
        pool = await self._memory.get_current_snapshot(question.warehouse_id)

        if question.entity_id is not None:
            history = await self._memory.get_entity_history(question.entity_id)
            if history is not None:
                entity, events = history
                pool = merge_evidence(
                    pool, RetrievedEvidence(entities=[entity], events=events)
                )

        if question.alert_id is not None:
            alert = await self._memory.get_alert(question.alert_id)
            if alert is not None:
                triggering_events = []
                if alert.event_id is not None:
                    event = await self._memory.get_event(alert.event_id)
                    if event is not None:
                        triggering_events.append(event)
                pool = merge_evidence(
                    pool, RetrievedEvidence(alerts=[alert], events=triggering_events)
                )

        return pool

    def _answer(
        self,
        question: CopilotQuestion,
        generated_at: datetime,
        answer: str,
        citations: list[Citation],
        *,
        grounded: bool,
    ) -> CopilotAnswer:
        return CopilotAnswer(
            question=question.question,
            warehouse_id=question.warehouse_id,
            generated_at=generated_at,
            answer=answer,
            citations=citations,
            grounded=grounded,
        )
