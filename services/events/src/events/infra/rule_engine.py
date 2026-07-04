"""Rule-based implementation of `domain.event_rule.EventRule`.

Stubbed out: rule composition and thresholds are follow-up work.
"""

from sentinel_common.schemas.detection import Detection
from sentinel_common.schemas.event import EventCreate
from events.domain.event_rule import EventRule


class RuleBasedEventExtractor(EventRule):
    def __init__(self, dwell_time_threshold_seconds: int) -> None:
        self._dwell_time_threshold_seconds = dwell_time_threshold_seconds

    def evaluate(self, detections: list[Detection]) -> list[EventCreate]:
        raise NotImplementedError
