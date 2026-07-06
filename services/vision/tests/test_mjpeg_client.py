import uuid
from collections.abc import AsyncIterator

import cv2
import httpx
import numpy as np
import pytest
from vision.infra.mjpeg_client import _iter_mjpeg_payloads, stream_frames

CAMERA_ID = uuid.uuid4()


def _jpeg_bytes(width: int = 8, height: int = 4) -> bytes:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok
    return buffer.tobytes()


def _part(payload: bytes) -> bytes:
    header = (
        f"--sentinelframe\r\nContent-Type: image/jpeg\r\n"
        f"Content-Length: {len(payload)}\r\n\r\n"
    )
    return header.encode() + payload + b"\r\n"


class _FakeStreamedResponse:
    """Duck-types the one method `_iter_mjpeg_payloads` needs from a response."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


async def test_iter_mjpeg_payloads_splits_multiple_parts_in_one_chunk() -> None:
    payload_a, payload_b = b"AAA", b"BBBB"
    body = _part(payload_a) + _part(payload_b)

    payloads = [p async for p in _iter_mjpeg_payloads(_FakeStreamedResponse([body]))]

    assert payloads == [payload_a, payload_b]


async def test_iter_mjpeg_payloads_handles_a_payload_split_across_chunks() -> None:
    payload = b"0123456789"
    part = _part(payload)
    split_at = len(part) - 5  # split partway through the payload/trailer
    chunks = [part[:split_at], part[split_at:]]

    payloads = [p async for p in _iter_mjpeg_payloads(_FakeStreamedResponse(chunks))]

    assert payloads == [payload]


async def test_iter_mjpeg_payloads_handles_a_header_split_across_chunks() -> None:
    payload = b"hello"
    part = _part(payload)
    split_at = 10  # somewhere inside the header block
    chunks = [part[:split_at], part[split_at:]]

    payloads = [p async for p in _iter_mjpeg_payloads(_FakeStreamedResponse(chunks))]

    assert payloads == [payload]


async def test_iter_mjpeg_payloads_resyncs_after_a_header_without_content_length() -> None:
    malformed = b"--sentinelframe\r\nContent-Type: image/jpeg\r\n\r\n"
    good_payload = b"real-payload"
    body = malformed + _part(good_payload)

    payloads = [p async for p in _iter_mjpeg_payloads(_FakeStreamedResponse([body]))]

    assert payloads == [good_payload]


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_stream_frames_yields_decoded_frames_with_incrementing_sequence() -> None:
    jpeg = _jpeg_bytes(width=8, height=4)
    body = _part(jpeg) + _part(jpeg)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    client = _mock_client(handler)

    frames = [f async for f in stream_frames(client, "http://ingestion:8001/x", CAMERA_ID)]

    assert [f.sequence for f in frames] == [1, 2]
    assert all(f.camera_id == CAMERA_ID for f in frames)
    assert frames[0].width == 8
    assert frames[0].height == 4
    assert frames[0].data == jpeg


async def test_stream_frames_raises_on_non_2xx_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    client = _mock_client(handler)

    with pytest.raises(httpx.HTTPStatusError):
        async for _ in stream_frames(client, "http://ingestion:8001/x", CAMERA_ID):
            pass
