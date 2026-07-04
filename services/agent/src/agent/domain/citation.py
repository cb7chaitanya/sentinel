"""The citation shape shared by every agent capability that must ground its output.

Both the reasoning agent's analysis (`domain/analysis.py`) and the
operations copilot's answers (`domain/copilot.py`) point back at real
warehouse-memory ids rather than asserting facts as free text -- this
module is the one place that shape is defined, so both grounding checks
(`domain/grounding.py`) work off the same `Citation`/`CitationKind`.
"""

from enum import StrEnum

from sentinel_common.schemas.common import SentinelModel


class CitationKind(StrEnum):
    EVENT = "event"
    ENTITY = "entity"
    INVENTORY_RECORD = "inventory_record"
    SAFETY_RULE = "safety_rule"
    ALERT = "alert"


class Citation(SentinelModel):
    """A pointer at one specific item in whatever context the model was given.

    `reference_id` is that item's id verbatim (an event's `id`, an
    entity's `entity_id`, an inventory record's `sku`, a safety rule's
    `id`, an alert's `id`) -- not a description of it. `detail` is a short
    human-readable excerpt for display; it is not itself evidence.
    """

    kind: CitationKind
    reference_id: str
    detail: str
