"""Consumes ingestion's live MJPEG relay and turns it back into `Frame`s.

Ingestion's `GET /streams/{camera_id}/mjpeg` (see
`services/ingestion/api/v1/streams.py`) is a `multipart/x-mixed-replace`
stream fed by its `FrameBroadcaster`: reusing it here means vision rides
the exact same fan-out a human dashboard viewer does -- a bounded,
drop-oldest queue per subscriber, so a slow vision service naturally
samples frames rather than falling behind on a growing backlog it could
never process in time anyway.

Each part is length-prefixed (`Content-Length`), so parsing never needs
to search for or even know the multipart boundary string -- only the
blank line ending a part's headers and the declared byte count that
follows it. That makes this immune to boundary-like byte sequences
appearing inside JPEG payload data, which a naive split-on-boundary
parser would not be.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import cv2
import httpx
import numpy as np
from sentinel_common.schemas.frame import Frame

_HEADER_TERMINATOR = b"\r\n\r\n"
_TRAILING_CRLF_LENGTH = 2


def _content_length(header: bytes) -> int | None:
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                return int(line.split(b":", 1)[1].strip())
            except ValueError:
                return None
    return None


async def _iter_mjpeg_payloads(response: httpx.Response) -> AsyncIterator[bytes]:
    """Split a multipart/x-mixed-replace response body into JPEG payloads."""
    buffer = bytearray()
    async for chunk in response.aiter_bytes():
        buffer.extend(chunk)
        while True:
            header_end = buffer.find(_HEADER_TERMINATOR)
            if header_end == -1:
                break

            content_length = _content_length(bytes(buffer[:header_end]))
            if content_length is None:
                # Not a part header we understand -- drop it and resync on
                # whatever comes after, rather than getting stuck forever.
                del buffer[: header_end + len(_HEADER_TERMINATOR)]
                continue

            payload_start = header_end + len(_HEADER_TERMINATOR)
            payload_end = payload_start + content_length
            if len(buffer) < payload_end + _TRAILING_CRLF_LENGTH:
                break  # incomplete part; wait for more bytes

            yield bytes(buffer[payload_start:payload_end])
            del buffer[: payload_end + _TRAILING_CRLF_LENGTH]


async def stream_frames(
    http_client: httpx.AsyncClient, mjpeg_url: str, camera_id: uuid.UUID
) -> AsyncIterator[Frame]:
    """Yield `Frame`s decoded from `mjpeg_url` until the connection drops.

    Raises on connection failure/drop rather than swallowing it -- the
    caller (see `core/detection_runner.py`) owns the reconnect/backoff
    policy, the same split of responsibility `OpenCvStreamReader` uses on
    the ingestion side.
    """
    sequence = 0
    async with http_client.stream("GET", mjpeg_url) as response:
        response.raise_for_status()
        async for payload in _iter_mjpeg_payloads(response):
            image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                continue
            height, width = image.shape[:2]
            sequence += 1
            yield Frame(
                camera_id=camera_id,
                sequence=sequence,
                captured_at=datetime.now(UTC),
                data=payload,
                width=width,
                height=height,
            )
