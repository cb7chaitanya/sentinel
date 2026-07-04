"""Domain schemas and interface for the operations copilot.

The copilot answers a single operator question (`CopilotQuestion`) using
only warehouse memory retrieved for it (`domain.evidence.RetrievedEvidence`)
-- retrieval happens before generation and is never skipped (see
`domain.retrieval` and `infra.copilot.MemoryBackedCopilot`). Unlike the
reasoning agent, which always returns whatever it finds, the copilot has
two fail-closed fallbacks baked into the contract: no evidence at all
means the LLM is never called, and an answer that doesn't cite its
evidence correctly is replaced rather than returned. Both use the fixed
strings below, so callers can distinguish "genuinely answered" from
"declined to answer" by checking `grounded` rather than by parsing text.
"""

import uuid
from datetime import datetime
from typing import Protocol

from pydantic import Field
from sentinel_common.schemas.common import SentinelModel

from agent.domain.citation import Citation

NO_EVIDENCE_ANSWER = (
    "I don't have any warehouse memory that matches this question, so I can't answer it."
)
UNGROUNDED_ANSWER_FALLBACK = (
    "I found related warehouse memory but couldn't produce an answer fully backed by it, "
    "so I won't guess."
)


class CopilotQuestion(SentinelModel):
    """One operator question, plus optional hints about what it's about.

    `entity_id`/`zone_name`/`alert_id` let a caller that already knows
    what's being asked about (e.g. a UI where the user clicked a specific
    alert) point retrieval directly at it, rather than relying only on
    best-effort keyword matching against the free-text `question`.
    """

    warehouse_id: uuid.UUID
    question: str = Field(min_length=1)
    entity_id: uuid.UUID | None = None
    zone_name: str | None = None
    alert_id: uuid.UUID | None = None


class CopilotAnswerContent(SentinelModel):
    """The part of the answer the model actually produces."""

    answer: str
    citations: list[Citation] = []


class CopilotAnswer(SentinelModel):
    question: str
    warehouse_id: uuid.UUID
    generated_at: datetime
    answer: str
    citations: list[Citation] = []
    grounded: bool


class OperationsCopilot(Protocol):
    async def answer(self, question: CopilotQuestion) -> CopilotAnswer: ...
