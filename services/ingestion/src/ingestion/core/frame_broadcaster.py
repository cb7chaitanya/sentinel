"""In-memory fan-out of captured frames to any number of live subscribers.

`StreamReader.frames()` is a single-consumer async generator per camera --
`StreamRegistry` already drains it exclusively to keep FPS/health stats
advancing (see `stream_registry.py`). Anything else that wants to see
frames (an MJPEG HTTP endpoint, eventually more than one) subscribes here
instead of trying to consume `frames()` itself, which only one caller
ever can.

Each subscriber gets its own bounded queue holding only the latest frame:
a slow HTTP client should lag behind live video, not accumulate an
unbounded backlog of stale frames it will never render in time.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator

from sentinel_common.schemas.frame import Frame


def _put_latest(queue: asyncio.Queue[Frame], frame: Frame) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    try:
        queue.put_nowait(frame)
    except asyncio.QueueFull:
        pass


class FrameBroadcaster:
    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue[Frame]]] = {}

    def publish(self, frame: Frame) -> None:
        for queue in self._subscribers.get(frame.camera_id, ()):
            _put_latest(queue, frame)

    async def subscribe(self, camera_id: uuid.UUID) -> AsyncIterator[Frame]:
        """Yield frames for `camera_id` as they're published, until cancelled."""
        queue: asyncio.Queue[Frame] = asyncio.Queue(maxsize=1)
        subscribers = self._subscribers.setdefault(camera_id, set())
        subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(camera_id, None)
