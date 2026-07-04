import uuid
from datetime import UTC, datetime

import cv2
import numpy as np
import pytest
import vision.infra.yolo_detector as yolo_detector_module
from sentinel_common.schemas.frame import Frame
from vision.infra.yolo_detector import YoloObjectDetector

CAMERA_ID = uuid.uuid4()


def _jpeg_bytes(width: int = 16, height: int = 12) -> bytes:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok
    return buffer.tobytes()


def _frame(data: bytes) -> Frame:
    return Frame(
        camera_id=CAMERA_ID,
        sequence=1,
        captured_at=datetime.now(UTC),
        data=data,
        width=16,
        height=12,
    )


class _FakeBox:
    def __init__(
        self, xyxy: tuple[float, float, float, float], cls_id: int, confidence: float
    ) -> None:
        self.xyxy = [xyxy]
        self.cls = [cls_id]
        self.conf = [confidence]


class _FakeResult:
    def __init__(self, boxes: list[_FakeBox], names: dict[int, str]) -> None:
        self.boxes = boxes
        self.names = names


class _FakeYolo:
    last_predict_kwargs: dict[str, object] = {}

    def __init__(self, weights_path: str) -> None:
        self.weights_path = weights_path

    def predict(self, image: np.ndarray, **kwargs: object) -> list[_FakeResult]:
        _FakeYolo.last_predict_kwargs = kwargs
        box = _FakeBox(xyxy=(1.0, 2.0, 3.0, 4.0), cls_id=0, confidence=0.75)
        return [_FakeResult(boxes=[box], names={0: "person"})]


@pytest.fixture(autouse=True)
def fake_yolo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(yolo_detector_module, "YOLO", _FakeYolo)


async def test_detect_maps_yolo_results_to_raw_detections() -> None:
    detector = YoloObjectDetector(weights_path="fake.pt", confidence_threshold=0.1, device="cpu")

    detections = await detector.detect(_frame(_jpeg_bytes()))

    assert len(detections) == 1
    detection = detections[0]
    assert detection.label == "person"
    assert detection.confidence == 0.75
    assert detection.bounding_box.x_min == 1.0
    assert detection.bounding_box.y_min == 2.0
    assert detection.bounding_box.x_max == 3.0
    assert detection.bounding_box.y_max == 4.0


async def test_detect_passes_confidence_threshold_and_device_to_the_model() -> None:
    detector = YoloObjectDetector(weights_path="fake.pt", confidence_threshold=0.42, device="cpu")

    await detector.detect(_frame(_jpeg_bytes()))

    assert _FakeYolo.last_predict_kwargs["conf"] == 0.42
    assert _FakeYolo.last_predict_kwargs["device"] == "cpu"


async def test_detect_returns_empty_list_for_undecodable_frame() -> None:
    detector = YoloObjectDetector(weights_path="fake.pt", confidence_threshold=0.1, device="cpu")

    detections = await detector.detect(_frame(b"not-a-real-jpeg"))

    assert detections == []
