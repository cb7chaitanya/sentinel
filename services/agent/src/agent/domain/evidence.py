"""What retrieval found: the copilot's only source of truth for one question.

`RetrievedEvidence` is deliberately the same shape whether it's the full
pool fetched from memory or the narrower slice `domain.retrieval` decides
is actually relevant -- retrieval is just "take a bigger bag, keep the
parts that matter," not a change of representation.

`entities` reuses `domain.context.EntitySnapshot` (already the agent's
local view of a memory entity, current-zone membership included).
`AlertRecord` is new here: alerts aren't part of the reasoning agent's
`AgentContext`, so there was nothing to reuse.
"""

import uuid
from datetime import datetime

from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.event import EventRead

from agent.domain.context import EntitySnapshot


class AlertRecord(SentinelModel):
    """An alert, as retrieved from memory -- enough to explain why it fired."""

    id: uuid.UUID
    severity: str
    status: str
    summary: str
    event_id: uuid.UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class RetrievedEvidence(SentinelModel):
    entities: list[EntitySnapshot] = []
    events: list[EventRead] = []
    alerts: list[AlertRecord] = []

    def is_empty(self) -> bool:
        return not (self.entities or self.events or self.alerts)


def merge_evidence(*bundles: RetrievedEvidence) -> RetrievedEvidence:
    """Union several bundles, deduplicating by each item's id.

    Used to fold hint-driven fetches (an entity's full history, a specific
    alert and its triggering event) into the base snapshot -- later
    bundles win on conflict, though in practice the same id never carries
    conflicting data since it all traces back to the same memory service.
    """
    entities: dict[uuid.UUID, EntitySnapshot] = {}
    events: dict[uuid.UUID, EventRead] = {}
    alerts: dict[uuid.UUID, AlertRecord] = {}

    for bundle in bundles:
        for entity in bundle.entities:
            entities[entity.entity_id] = entity
        for event in bundle.events:
            events[event.id] = event
        for alert in bundle.alerts:
            alerts[alert.id] = alert

    return RetrievedEvidence(
        entities=list(entities.values()),
        events=list(events.values()),
        alerts=list(alerts.values()),
    )
