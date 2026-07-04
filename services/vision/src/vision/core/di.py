"""Composition root for the vision service's dependencies."""

from typing import Annotated

from fastapi import Depends
from sentinel_common.di import singleton

from vision.core.config import Settings, get_settings
from vision.core.pipeline import VisionPipeline
from vision.domain.detector import ObjectDetector
from vision.domain.tracker import ObjectTrackerFactory
from vision.infra.byte_tracker import ByteTrackerFactory
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


ObjectDetectorDep = Annotated[ObjectDetector, Depends(get_object_detector)]
ObjectTrackerFactoryDep = Annotated[ObjectTrackerFactory, Depends(get_tracker_factory)]
VisionPipelineDep = Annotated[VisionPipeline, Depends(get_vision_pipeline)]
