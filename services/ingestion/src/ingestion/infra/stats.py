"""Pure in-memory bookkeeping for a single stream's throughput and health.

No OpenCV or FastAPI imports here: this is plain arithmetic over
timestamps, kept separate from `OpenCvStreamReader` so it can be unit
tested without a real capture device.
"""

import uuid
from collections import deque
from datetime import datetime

from ingestion.domain.camera import ConnectionState, StreamHealth

_FPS_WINDOW = 30


class StreamStatsTracker:
    """Tracks FPS, dropped frames, reconnects, and connection state for one stream."""

    def __init__(self, camera_id: uuid.UUID) -> None:
        self._camera_id = camera_id
        self._state = ConnectionState.CONNECTING
        self._frames_read = 0
        self._frames_dropped = 0
        self._reconnect_count = 0
        self._last_frame_at: datetime | None = None
        self._connected_since: datetime | None = None
        self._recent_frame_times: deque[datetime] = deque(maxlen=_FPS_WINDOW)

    def set_state(self, state: ConnectionState) -> None:
        self._state = state
        if state is not ConnectionState.CONNECTED:
            # Stale samples from before a disconnect shouldn't inflate the
            # reported fps while no frames are currently arriving.
            self._recent_frame_times.clear()
            self._connected_since = None

    def mark_connected(self, at: datetime) -> None:
        self._state = ConnectionState.CONNECTED
        self._connected_since = at

    def record_frame(self, at: datetime) -> None:
        self._frames_read += 1
        self._last_frame_at = at
        self._recent_frame_times.append(at)

    def record_drop(self) -> None:
        self._frames_dropped += 1

    def record_reconnect(self) -> None:
        self._reconnect_count += 1

    @property
    def fps(self) -> float:
        if len(self._recent_frame_times) < 2:
            return 0.0
        span = (self._recent_frame_times[-1] - self._recent_frame_times[0]).total_seconds()
        if span <= 0:
            return 0.0
        return (len(self._recent_frame_times) - 1) / span

    def snapshot(self) -> StreamHealth:
        return StreamHealth(
            camera_id=self._camera_id,
            state=self._state,
            fps=round(self.fps, 2),
            frames_read=self._frames_read,
            frames_dropped=self._frames_dropped,
            reconnect_count=self._reconnect_count,
            last_frame_at=self._last_frame_at,
            connected_since=self._connected_since,
        )
