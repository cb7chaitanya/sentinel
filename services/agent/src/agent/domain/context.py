"""Domain input schemas: what the agent is given to reason over.

This is the agent's *only* source of truth -- see `domain/grounding.py` for
how every conclusion it produces is checked against exactly these ids, so
it can never cite something that wasn't actually provided.

These stay local to the agent service rather than in `sentinel_common`:
`recent_events` reuses the shared `EventRead` (a genuine cross-service
boundary type memory produces), but the snapshot/record shapes here are
this service's own view of "what to hand the model", not a wire format any
other service currently produces or consumes.
"""

import uuid
from datetime import datetime

from pydantic import Field
from sentinel_common.schemas.common import SentinelModel
from sentinel_common.schemas.event import EventRead


class ZoneMembership(SentinelModel):
    """One zone an entity is currently inside, and how long it's been there."""

    zone_name: str
    dwell_time_seconds: float = Field(ge=0.0)


class EntitySnapshot(SentinelModel):
    """A tracked entity (worker, forklift, pallet, box, ...) as of now."""

    entity_id: uuid.UUID
    entity_type: str
    label: str
    camera_id: uuid.UUID
    last_seen_at: datetime
    current_zones: list[ZoneMembership] = []


class WarehouseStateSnapshot(SentinelModel):
    warehouse_id: uuid.UUID
    generated_at: datetime
    entities: list[EntitySnapshot] = []


class InventoryRecord(SentinelModel):
    """One SKU's expected inventory, as of the last count."""

    sku: str
    description: str
    expected_quantity: int = Field(ge=0)
    zone_name: str | None = None
    last_counted_at: datetime | None = None


class SafetyRule(SentinelModel):
    """A warehouse safety policy the agent should reason against."""

    id: str
    description: str
    applies_to_zone: str | None = None
    applies_to_entity_type: str | None = None
    severity: str


class AgentContext(SentinelModel):
    """Everything the agent may draw on. It must never reason beyond this."""

    warehouse_state: WarehouseStateSnapshot
    recent_events: list[EventRead] = []
    inventory_records: list[InventoryRecord] = []
    safety_rules: list[SafetyRule] = []
