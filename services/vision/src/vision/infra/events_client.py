"""Thin async HTTP client for pushing detections downstream to events.

Vision and events are separate deployables, so this is a plain HTTP
boundary (`httpx`), not an in-process import -- the same shape as
`events.infra.memory_client.MemoryClient` on the other side of that hop.
"""

import httpx
from sentinel_common.schemas.detection import FrameDetections


class EventsClient:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    async def post_detections(self, frame_detections: FrameDetections) -> None:
        response = await self._http.post(
            f"{self._base_url}/api/v1/detections",
            content=frame_detections.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
