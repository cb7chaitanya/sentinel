"""Composition root for the gateway's dependencies.

Downstream service clients are constructed here and wired into routers via
FastAPI's `Depends()`. No business/orchestration logic lives in this file.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import httpx
from fastapi import Depends

from gateway.core.config import Settings, get_settings


async def get_http_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
