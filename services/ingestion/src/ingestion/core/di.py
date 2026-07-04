"""Composition root for the ingestion service's dependencies.

API routes depend on the `StreamRegistry`, which in turn depends only on
the `StreamReaderFactory`/`StreamReader` Protocols (see `domain/camera.py`)
-- never on the concrete OpenCV adapter directly. Swapping the capture
backend later means changing only this file.
"""

from typing import Annotated

from fastapi import Depends
from sentinel_common.di import singleton

from ingestion.core.config import Settings, get_settings
from ingestion.core.stream_registry import StreamRegistry
from ingestion.domain.camera import StreamReaderFactory
from ingestion.infra.opencv_capture import OpenCvStreamReaderFactory

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_stream_reader_factory() -> StreamReaderFactory:
    settings = get_settings()
    return OpenCvStreamReaderFactory(
        initial_backoff_seconds=settings.reconnect_initial_backoff_seconds,
        max_backoff_seconds=settings.reconnect_max_backoff_seconds,
        max_consecutive_read_failures=settings.max_consecutive_read_failures,
    )


@singleton
def get_stream_registry() -> StreamRegistry:
    settings = get_settings()
    return StreamRegistry(get_stream_reader_factory(), settings.camera_sources)


StreamReaderFactoryDep = Annotated[StreamReaderFactory, Depends(get_stream_reader_factory)]
StreamRegistryDep = Annotated[StreamRegistry, Depends(get_stream_registry)]
