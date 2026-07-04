import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from ingestion.core.frame_broadcaster import FrameBroadcaster
from sentinel_common.schemas.frame import Frame

CAMERA_ID = uuid.uuid4()


def _frame(sequence: int) -> Frame:
    return Frame(
        camera_id=CAMERA_ID,
        sequence=sequence,
        captured_at=datetime.now(UTC),
        data=f"frame-{sequence}".encode(),
        width=1,
        height=1,
    )


async def _pending_next(subscription: AsyncIterator[Frame]) -> asyncio.Task[Frame]:
    """Start consuming `subscription` and wait until it's actually registered.

    `subscribe()` is an async generator: nothing in its body runs (including
    registering the subscriber queue) until it's first iterated. Calling
    `publish()` right after `subscribe()` -- before anything has pumped the
    generator -- would be a lost update, exactly like publishing before a
    real HTTP client's `async for` loop starts. This mirrors the real
    endpoint's timing by starting the read as a background task and
    yielding control once so the generator runs up to its first suspend
    point (`await queue.get()`) before the test publishes anything.
    """
    task = asyncio.ensure_future(subscription.__anext__())
    await asyncio.sleep(0)
    return task


async def test_subscriber_receives_a_published_frame() -> None:
    broadcaster = FrameBroadcaster()
    subscription = broadcaster.subscribe(CAMERA_ID)
    pending = await _pending_next(subscription)

    broadcaster.publish(_frame(1))
    frame = await asyncio.wait_for(pending, timeout=1.0)

    assert frame.sequence == 1


async def test_publish_with_no_subscribers_does_not_raise() -> None:
    broadcaster = FrameBroadcaster()

    broadcaster.publish(_frame(1))  # should simply be a no-op


async def test_each_subscriber_gets_its_own_copy() -> None:
    broadcaster = FrameBroadcaster()
    first_pending = await _pending_next(broadcaster.subscribe(CAMERA_ID))
    second_pending = await _pending_next(broadcaster.subscribe(CAMERA_ID))

    broadcaster.publish(_frame(1))

    assert (await asyncio.wait_for(first_pending, timeout=1.0)).sequence == 1
    assert (await asyncio.wait_for(second_pending, timeout=1.0)).sequence == 1


async def test_slow_subscriber_only_sees_the_latest_frame() -> None:
    broadcaster = FrameBroadcaster()
    pending = await _pending_next(broadcaster.subscribe(CAMERA_ID))

    broadcaster.publish(_frame(1))
    broadcaster.publish(_frame(2))  # published before the subscriber reads frame 1

    frame = await asyncio.wait_for(pending, timeout=1.0)

    assert frame.sequence == 2


async def test_frames_for_a_different_camera_are_not_delivered() -> None:
    broadcaster = FrameBroadcaster()
    pending = await _pending_next(broadcaster.subscribe(CAMERA_ID))

    other_camera_frame = Frame(
        camera_id=uuid.uuid4(),
        sequence=1,
        captured_at=datetime.now(UTC),
        data=b"other",
        width=1,
        height=1,
    )
    broadcaster.publish(other_camera_frame)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(pending, timeout=0.05)
    pending.cancel()
