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
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel


class CitationKind(StrEnum):
    EVENT = "event"
    ENTITY = "entity"
    INVENTORY_RECORD = "inventory_record"
    SAFETY_RULE = "safety_rule"


class Citation(SentinelModel):
    """A pointer at one specific item in the `AgentContext`.

    `reference_id` is that item's id verbatim (an event's `id`, an
    entity's `entity_id`, an inventory record's `sku`, a safety rule's
    `id`) -- not a description of it. `detail` is a short human-readable
    excerpt for display; it is not itself evidence.
    """

    kind: CitationKind
    reference_id: str
    detail: str


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
