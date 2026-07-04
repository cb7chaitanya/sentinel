"""Domain output schemas: the agent's structured, grounded analysis.

Every Insight/PotentialIssue/Recommendation carries `citations` pointing at
specific items in the `AgentContext` it was given -- an id reference the
model supplies, not free text. `domain.grounding` is what actually verifies
those references are real; this module only defines the shape, and
deliberately does not enforce "at least one citation" here (see that
module's docstring for why that check belongs there instead of in the
schema).

`AnalysisContent` is exactly what the model is asked to produce;
`AgentAnalysis` wraps it with the envelope fields (`warehouse_id`,
`generated_at`) supplied by the caller from `AgentContext`, not by the
model -- there's no reason to ask an LLM to echo back facts the caller
already knows for certain.

`Citation`/`CitationKind` live in `domain/citation.py` and are re-exported
here for backwards compatibility with existing imports -- the operations
copilot (`domain/copilot.py`) needs the same shape for its own grounded
answers, so they moved to a module neither capability owns.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel

from agent.domain.citation import Citation, CitationKind

__all__ = [
    "AgentAnalysis",
    "AnalysisContent",
    "Citation",
    "CitationKind",
    "Insight",
    "PotentialIssue",
    "Recommendation",
    "Severity",
]


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Insight(SentinelModel):
    id: str
    summary: str
    citations: list[Citation] = []


class PotentialIssue(SentinelModel):
    id: str
    summary: str
    severity: Severity
    citations: list[Citation] = []


class Recommendation(SentinelModel):
    id: str
    summary: str
    rationale: str
    citations: list[Citation] = []


class AnalysisContent(SentinelModel):
    """The part of the analysis the model actually produces."""

    insights: list[Insight] = []
    potential_issues: list[PotentialIssue] = []
    recommendations: list[Recommendation] = []


class AgentAnalysis(AnalysisContent):
    warehouse_id: uuid.UUID
    generated_at: datetime
