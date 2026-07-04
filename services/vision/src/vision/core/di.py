"""Composition root for the vision service's dependencies."""

from typing import Annotated

from fastapi import Depends

from sentinel_common.di import singleton
from vision.core.config import Settings, get_settings
from vision.domain.detector import ObjectDetector
from vision.infra.yolo_detector import YoloObjectDetector

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_object_detector() -> ObjectDetector:
    settings = get_settings()
    return YoloObjectDetector(
        weights_path=settings.model_weights_path,
        confidence_threshold=settings.confidence_threshold,
        device=settings.device,
    )


ObjectDetectorDep = Annotated[ObjectDetector, Depends(get_object_detector)]
