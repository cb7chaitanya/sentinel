import uuid
from datetime import UTC, datetime, timedelta

from ingestion.domain.camera import ConnectionState
from ingestion.infra.stats import StreamStatsTracker

CAMERA_ID = uuid.uuid4()


def test_initial_snapshot_is_connecting_with_no_activity() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)

    health = tracker.snapshot()

    assert health.camera_id == CAMERA_ID
    assert health.state is ConnectionState.CONNECTING
    assert health.fps == 0.0
    assert health.frames_read == 0
    assert health.frames_dropped == 0
    assert health.reconnect_count == 0
    assert health.last_frame_at is None
    assert health.connected_since is None


def test_fps_is_computed_from_recent_frame_spacing() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)
    start = datetime.now(UTC)

    for i in range(10):
        tracker.record_frame(start + timedelta(seconds=i * 0.1))

    health = tracker.snapshot()

    assert health.frames_read == 10
    assert health.fps == 10.0  # 9 intervals of 0.1s each = 10 frames/sec


def test_single_frame_reports_zero_fps() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)

    tracker.record_frame(datetime.now(UTC))

    assert tracker.snapshot().fps == 0.0


def test_dropped_and_reconnect_counters_accumulate() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)

    tracker.record_drop()
    tracker.record_drop()
    tracker.record_reconnect()

    health = tracker.snapshot()
    assert health.frames_dropped == 2
    assert health.reconnect_count == 1


def test_mark_connected_sets_state_and_connected_since() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)
    now = datetime.now(UTC)

    tracker.mark_connected(now)

    health = tracker.snapshot()
    assert health.state is ConnectionState.CONNECTED
    assert health.connected_since == now


def test_disconnecting_clears_fps_window_and_connected_since() -> None:
    tracker = StreamStatsTracker(CAMERA_ID)
    now = datetime.now(UTC)
    tracker.mark_connected(now)
    tracker.record_frame(now)
    tracker.record_frame(now + timedelta(seconds=0.1))
    assert tracker.snapshot().fps > 0.0

    tracker.set_state(ConnectionState.RECONNECTING)

    health = tracker.snapshot()
    assert health.state is ConnectionState.RECONNECTING
    assert health.fps == 0.0
    assert health.connected_since is None
    # Historical counters are not reset by a disconnect.
    assert health.frames_read == 2
