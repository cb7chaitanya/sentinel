"""Proxies the ingestion service's stream health and live MJPEG feeds.

The MJPEG endpoint is a real passthrough, not a buffered proxy: it streams
bytes through as ingestion produces them (via `client.send(..., stream=True)`
plus a `StreamingResponse`), so the dashboard's live camera panel sees the
same live video ingestion does, just relayed through the gateway rather
than requiring the browser to reach ingestion directly.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from gateway.core.di import HttpClientDep, SettingsDep

router = APIRouter()


@router.get("/cameras/streams")
async def list_camera_streams(client: HttpClientDep, settings: SettingsDep) -> list[dict[str, Any]]:
    response = await client.get(f"{settings.ingestion_service_url}/api/v1/streams")
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@router.get("/cameras/{camera_id}/mjpeg")
async def camera_mjpeg(
    camera_id: uuid.UUID, client: HttpClientDep, settings: SettingsDep
) -> StreamingResponse:
    upstream_request = client.build_request(
        "GET", f"{settings.ingestion_service_url}/api/v1/streams/{camera_id}/mjpeg"
    )
    upstream_response = await client.send(upstream_request, stream=True)

    if upstream_response.status_code >= 400:
        await upstream_response.aclose()
        raise HTTPException(
            status_code=upstream_response.status_code,
            detail=f"no configured stream for camera {camera_id}",
        )

    return StreamingResponse(
        upstream_response.aiter_bytes(),
        media_type=upstream_response.headers.get("content-type", "multipart/x-mixed-replace"),
        background=BackgroundTask(upstream_response.aclose),
    )
