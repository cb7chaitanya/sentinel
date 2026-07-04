"""Deterministic narrowing of a fetched evidence pool down to one question.

This is not semantic search: it's plain keyword and id matching, on
purpose. `infra.copilot` decides *what to fetch* from memory (a targeted
entity's full history, a specific alert and its triggering event); this
module only decides, given whatever was fetched, which of it is actually
relevant to `question` -- a pure function of two already-in-memory
values, with no I/O, so it's exhaustively unit-testable without a network
or an LLM in the loop.

Explicit hints (`entity_id`/`zone_name`/`alert_id`) always take priority
over free text, since they're exact. Free-text matching only recognizes
entity-type words ("pallet", "forklift", "worker", "box") and zone names
that are already present somewhere in the pool -- it cannot resolve an
arbitrary human-friendly code like "P103" against an internal id, and
does not pretend to; unmatched text simply narrows nothing, and the
caller ends up with the broader (still real, still cited) evidence
instead of a guess.
"""

import re

from sentinel_common.schemas.event import EventRead

from agent.domain.context import EntitySnapshot
from agent.domain.copilot import CopilotQuestion
from agent.domain.evidence import AlertRecord, RetrievedEvidence

_ENTITY_TYPE_SINGULAR = {
    "worker": "worker",
    "workers": "worker",
    "forklift": "forklift",
    "forklifts": "forklift",
    "pallet": "pallet",
    "pallets": "pallet",
    "box": "box",
    "boxes": "box",
}

_CODE_PATTERN = re.compile(r"[A-Za-z]+-?\d+")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9-]+")


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)}


def _mentioned_entity_types(tokens: set[str]) -> set[str]:
    return {_ENTITY_TYPE_SINGULAR[tok] for tok in tokens if tok in _ENTITY_TYPE_SINGULAR}


def _mentioned_codes(text: str) -> set[str]:
    return {match.group(0).lower() for match in _CODE_PATTERN.finditer(text)}


def _known_zone_names(pool: RetrievedEvidence) -> set[str]:
    names = {zone.zone_name for entity in pool.entities for zone in entity.current_zones}
    names |= {event.zone_name for event in pool.events if event.zone_name is not None}
    return names


def _mentioned_zone_names(question: CopilotQuestion, pool: RetrievedEvidence) -> set[str]:
    zone_names = {question.zone_name.lower()} if question.zone_name else set()
    lowered_question = question.question.lower()
    zone_names |= {
        name.lower() for name in _known_zone_names(pool) if name.lower() in lowered_question
    }
    return zone_names


def _entity_is_relevant(
    entity: EntitySnapshot,
    *,
    question: CopilotQuestion,
    types: set[str],
    codes: set[str],
    zone_names: set[str],
) -> bool:
    if question.entity_id is not None:
        return entity.entity_id == question.entity_id
    if not types and not codes and not zone_names:
        return True
    if entity.entity_type.lower() in types:
        return True
    if codes and any(
        code in str(entity.entity_id).lower() or code in entity.label.lower() for code in codes
    ):
        return True
    return bool(
        zone_names and any(z.zone_name.lower() in zone_names for z in entity.current_zones)
    )


def _event_is_relevant(event: EventRead, *, zone_names: set[str]) -> bool:
    if not zone_names:
        return True
    return event.zone_name is not None and event.zone_name.lower() in zone_names


def _alert_is_relevant(alert: AlertRecord, *, question: CopilotQuestion) -> bool:
    if question.alert_id is not None:
        return alert.id == question.alert_id
    return True


def retrieve_evidence(question: CopilotQuestion, pool: RetrievedEvidence) -> RetrievedEvidence:
    """Narrow `pool` (everything fetched) down to what's relevant to `question`."""
    tokens = _tokens(question.question)
    types = _mentioned_entity_types(tokens)
    codes = _mentioned_codes(question.question)
    zone_names = _mentioned_zone_names(question, pool)

    return RetrievedEvidence(
        entities=[
            e
            for e in pool.entities
            if _entity_is_relevant(
                e, question=question, types=types, codes=codes, zone_names=zone_names
            )
        ],
        events=[e for e in pool.events if _event_is_relevant(e, zone_names=zone_names)],
        alerts=[a for a in pool.alerts if _alert_is_relevant(a, question=question)],
    )
