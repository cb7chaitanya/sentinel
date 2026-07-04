"""Composition root for the events service's dependencies."""

from typing import Annotated

from fastapi import Depends
from sentinel_common.di import singleton

from events.core.config import Settings, get_settings
from events.core.event_engine import EventEngine
from events.domain.event_rule import EventRule
from events.domain.zone_engine import ZoneEngine
from events.infra.polygon_zone_engine import PolygonZoneEngine
from events.infra.rule_engine import RuleBasedEventExtractor

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_event_rule_engine(settings: SettingsDep) -> EventRule:
    return RuleBasedEventExtractor(
        dwell_time_threshold_seconds=settings.dwell_time_threshold_seconds
    )


@singleton
def get_zone_engine() -> ZoneEngine:
    settings = get_settings()
    return PolygonZoneEngine(
        settings.zones,
        exit_grace_period_seconds=settings.zone_exit_grace_period_seconds,
    )


@singleton
def get_event_engine() -> EventEngine:
    settings = get_settings()
    return EventEngine(
        get_zone_engine(),
        motion_speed_threshold=settings.motion_speed_threshold,
        worker_labels=settings.worker_labels,
        worker_display_name=settings.worker_display_name,
    )


EventRuleDep = Annotated[EventRule, Depends(get_event_rule_engine)]
ZoneEngineDep = Annotated[ZoneEngine, Depends(get_zone_engine)]
EventEngineDep = Annotated[EventEngine, Depends(get_event_engine)]
