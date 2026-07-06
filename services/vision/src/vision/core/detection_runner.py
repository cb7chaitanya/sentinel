"""Drives the vision pipeline from ingestion's live camera streams.

Mirrors ingestion's own `StreamRegistry`: one reconnecting background
task per camera, started on `start()` and cancelled on `stop()`. Cameras
are discovered once at startup from ingestion's `GET /streams` -- there's
no camera registry yet (see `ingestion.domain.camera.CameraRegistry`) to
watch for cameras added after that, the same limitation ingestion itself
has with its own static `CAMERA_SOURCES` config.

A camera's task never dies permanently: a dropped MJPEG connection (the
ingestion process restarting, a network blip) reconnects with the same
exponential-backoff shape `OpenCvStreamReader` uses on the ingestion
side, and a single frame that fails to process (a bad decode, a detector
exception) is logged and skipped rather than tearing down the whole
camera's task over one bad frame.
"""

import asyncio
import logging
import uuid

import httpx
from sentinel_common.schemas.frame import Frame

from vision.core.pipeline import VisionPipeline
from vision.infra.events_client import EventsClient
from vision.infra.mjpeg_client import stream_frames

logger = logging.getLogger(__name__)


class DetectionPipelineRunner:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        pipeline: VisionPipeline,
        events: EventsClient,
        *,
        ingestion_service_url: str,
        initial_backoff_seconds: float,
        max_backoff_seconds: float,
    ) -> None:
        self._http = http_client
        self._pipeline = pipeline
        self._events = events
        self._ingestion_base_url = ingestion_service_url.rstrip("/")
        self._initial_backoff_seconds = initial_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def start(self) -> None:
        for camera_id in await self._discover_cameras():
            self._tasks[camera_id] = asyncio.create_task(
                self._run_camera(camera_id), name=f"vision-camera-{camera_id}"
            )

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _discover_cameras(self) -> list[uuid.UUID]:
        try:
            response = await self._http.get(f"{self._ingestion_base_url}/api/v1/streams")
            response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("failed to discover cameras from ingestion", exc_info=True)
            return []
        return [uuid.UUID(stream["camera_id"]) for stream in response.json()]

    async def _run_camera(self, camera_id: uuid.UUID) -> None:
        mjpeg_url = f"{self._ingestion_base_url}/api/v1/streams/{camera_id}/mjpeg"
        backoff = self._initial_backoff_seconds
        while True:
            try:
                async for frame in stream_frames(self._http, mjpeg_url, camera_id):
                    backoff = self._initial_backoff_seconds
                    await self._process_and_forward(frame)
            except asyncio.CancelledError:
                raise
            except httpx.HTTPError:
                logger.warning(
                    "camera %s: mjpeg stream error, reconnecting in %.1fs",
                    camera_id,
                    backoff,
                    exc_info=True,
                )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self._max_backoff_seconds)

    async def _process_and_forward(self, frame: Frame) -> None:
        try:
            detections = await self._pipeline.process(frame)
        except Exception:
            logger.exception(
                "camera %s: detection pipeline failed on frame %d",
                frame.camera_id,
                frame.sequence,
            )
            return

        try:
            await self._events.post_detections(detections)
        except httpx.HTTPError:
            logger.warning(
                "camera %s: failed to forward detections to events",
                frame.camera_id,
                exc_info=True,
            )
