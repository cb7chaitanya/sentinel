"""Domain-level interface for turning a stream of detections into events.

Concrete rule implementations (threshold-based, learned, etc.) live behind
`infra/rule_engine.py` and implement this Protocol.
"""

from typing import Protocol

from sentinel_common.schemas.detection import Detection
from sentinel_common.schemas.event import EventCreate


class EventRule(Protocol):
    """A single rule that inspects detections and may emit an event."""

    def evaluate(self, detections: list[Detection]) -> list[EventCreate]: ...
