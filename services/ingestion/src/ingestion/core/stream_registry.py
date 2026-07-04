"""Runtime orchestration of the configured camera streams.

Owns the lifecycle of one `StreamReader` per configured `StreamSource`:
opens it, continuously drains its `frames()` iterator on a background task
(so FPS/health stats keep advancing even though nothing else is consuming
frames yet), and tears everything down on shutdown. Depends only on the
domain `StreamReaderFactory`/`StreamReader` Protocols, never on OpenCV.
"""

import asyncio
import logging
import uuid

from ingestion.domain.camera import StreamHealth, StreamReader, StreamReaderFactory, StreamSource

logger = logging.getLogger(__name__)


class StreamRegistry:
    def __init__(self, factory: StreamReaderFactory, sources: list[StreamSource]) -> None:
        self._factory = factory
        self._sources = sources
        self._readers: dict[uuid.UUID, StreamReader] = {}
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def start(self) -> None:
        for source in self._sources:
            reader = self._factory.create(source)
            self._readers[source.camera_id] = reader
            self._tasks[source.camera_id] = asyncio.create_task(
                self._drain(source.camera_id, reader),
                name=f"stream-drain-{source.camera_id}",
            )

    async def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        for reader in self._readers.values():
            await reader.close()
        self._tasks.clear()
        self._readers.clear()

    async def health(self, camera_id: uuid.UUID) -> StreamHealth | None:
        reader = self._readers.get(camera_id)
        if reader is None:
            return None
        return await reader.health()

    async def list_health(self) -> list[StreamHealth]:
        return [await reader.health() for reader in self._readers.values()]

    @staticmethod
    async def _drain(camera_id: uuid.UUID, reader: StreamReader) -> None:
        try:
            async for _ in reader.frames():
                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("stream drain task for camera %s exited unexpectedly", camera_id)
