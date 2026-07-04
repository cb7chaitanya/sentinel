"""Ultralytics YOLO-backed implementation of `domain.detector.ObjectDetector`.

Deliberately returns candidate boxes down to a low confidence floor (see
`min_confidence` in `core/config.py`) rather than a strict display
threshold: the tracker (ByteTrack) needs both high- and low-confidence
detections to recover temporarily-occluded objects, so filtering too
aggressively here would defeat its second matching pass.
"""

import asyncio
import logging

import cv2
import numpy as np
from sentinel_common.schemas.detection import BoundingBox
from sentinel_common.schemas.frame import Frame
from ultralytics import YOLO

from vision.domain.detector import ObjectDetector, RawDetection

logger = logging.getLogger(__name__)


class YoloObjectDetector(ObjectDetector):
    def __init__(self, weights_path: str, confidence_threshold: float, device: str) -> None:
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._model = YOLO(weights_path)

    async def detect(self, frame: Frame) -> list[RawDetection]:
        return await asyncio.to_thread(self._detect_sync, frame)

    def _detect_sync(self, frame: Frame) -> list[RawDetection]:
        image = cv2.imdecode(np.frombuffer(frame.data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            logger.warning("camera %s: could not decode frame %d", frame.camera_id, frame.sequence)
            return []

        results = self._model.predict(
            image,
            conf=self._confidence_threshold,
            device=self._device,
            verbose=False,
        )[0]

        detections: list[RawDetection] = []
        for box in results.boxes:
            x_min, y_min, x_max, y_max = (float(v) for v in box.xyxy[0])
            detections.append(
                RawDetection(
                    label=results.names[int(box.cls[0])],
                    confidence=float(box.conf[0]),
                    bounding_box=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
                )
            )
        return detections
