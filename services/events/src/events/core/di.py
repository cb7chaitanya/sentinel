"""Composition root for the events service's dependencies."""

from typing import Annotated

from fastapi import Depends

from events.core.config import Settings, get_settings
from events.domain.event_rule import EventRule
from events.infra.rule_engine import RuleBasedEventExtractor

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_event_rule_engine(settings: SettingsDep) -> EventRule:
    return RuleBasedEventExtractor(dwell_time_threshold_seconds=settings.dwell_time_threshold_seconds)


EventRuleDep = Annotated[EventRule, Depends(get_event_rule_engine)]
