"""Composition root for the vision service's dependencies."""

from typing import Annotated

import httpx
from fastapi import Depends
from sentinel_common.di import singleton

from vision.core.config import Settings, get_settings
from vision.core.detection_runner import DetectionPipelineRunner
from vision.core.pipeline import VisionPipeline
from vision.domain.detector import ObjectDetector
from vision.domain.tracker import ObjectTrackerFactory
from vision.infra.byte_tracker import ByteTrackerFactory
from vision.infra.events_client import EventsClient
from vision.infra.yolo_detector import YoloObjectDetector

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_object_detector() -> ObjectDetector:
    settings = get_settings()
    return YoloObjectDetector(
        weights_path=settings.model_weights_path,
        confidence_threshold=settings.min_confidence,
        device=settings.device,
    )


@singleton
def get_tracker_factory() -> ObjectTrackerFactory:
    settings = get_settings()
    return ByteTrackerFactory(
        high_confidence_threshold=settings.tracker_high_confidence_threshold,
        low_confidence_threshold=settings.min_confidence,
        iou_threshold=settings.tracker_iou_threshold,
        max_missed_frames=settings.tracker_max_missed_frames,
    )


@singleton
def get_vision_pipeline() -> VisionPipeline:
    return VisionPipeline(get_object_detector(), get_tracker_factory())


@singleton
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


@singleton
def get_events_client() -> EventsClient:
    settings = get_settings()
    return EventsClient(get_http_client(), base_url=settings.events_service_url)


@singleton
def get_detection_pipeline_runner() -> DetectionPipelineRunner:
    settings = get_settings()
    return DetectionPipelineRunner(
        get_http_client(),
        get_vision_pipeline(),
        get_events_client(),
        ingestion_service_url=settings.ingestion_service_url,
        initial_backoff_seconds=settings.detection_reconnect_initial_backoff_seconds,
        max_backoff_seconds=settings.detection_reconnect_max_backoff_seconds,
    )


ObjectDetectorDep = Annotated[ObjectDetector, Depends(get_object_detector)]
ObjectTrackerFactoryDep = Annotated[ObjectTrackerFactory, Depends(get_tracker_factory)]
VisionPipelineDep = Annotated[VisionPipeline, Depends(get_vision_pipeline)]
HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
EventsClientDep = Annotated[EventsClient, Depends(get_events_client)]
