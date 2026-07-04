"""Proxies the agent service's operations copilot for the dashboard's chat panel."""

from typing import Any

from fastapi import APIRouter, HTTPException

from gateway.core.di import HttpClientDep, SettingsDep

router = APIRouter()


@router.post("/copilot/ask")
async def ask_copilot(
    question: dict[str, Any], client: HttpClientDep, settings: SettingsDep
) -> dict[str, Any]:
    response = await client.post(
        f"{settings.agent_service_url}/api/v1/copilot/ask", json=question
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
