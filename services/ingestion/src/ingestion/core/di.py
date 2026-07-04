"""Composition root for the ingestion service's dependencies.

API routes depend on the `StreamReader` Protocol (see `domain/camera.py`),
never on the concrete `RtspStreamReader` adapter directly. Swapping the
capture backend later means changing only this file.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from ingestion.core.config import Settings, get_settings
from ingestion.domain.camera import StreamReader
from ingestion.infra.rtsp_client import RtspStreamReader

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_stream_reader_factory(settings: SettingsDep) -> Callable[[str], StreamReader]:
    def _build(rtsp_url: str) -> StreamReader:
        return RtspStreamReader(rtsp_url)

    return _build


StreamReaderFactoryDep = Annotated[Callable[[str], StreamReader], Depends(get_stream_reader_factory)]
