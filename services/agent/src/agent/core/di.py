"""Composition root for the agent service's dependencies."""

from typing import Annotated

import httpx
from anthropic import AsyncAnthropic
from fastapi import Depends
from sentinel_common.di import singleton

from agent.core.config import Settings, get_settings
from agent.domain.agent import WarehouseAgent
from agent.domain.copilot import OperationsCopilot
from agent.infra.copilot import MemoryBackedCopilot
from agent.infra.llm_client import AnthropicWarehouseAgent
from agent.infra.memory_client import MemoryClient

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_anthropic_client() -> AsyncAnthropic:
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


@singleton
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


def get_warehouse_agent(
    client: Annotated[AsyncAnthropic, Depends(get_anthropic_client)],
    settings: SettingsDep,
) -> WarehouseAgent:
    return AnthropicWarehouseAgent(client=client, model=settings.agent_model)


def get_memory_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: SettingsDep,
) -> MemoryClient:
    return MemoryClient(http_client=http_client, base_url=settings.memory_service_url)


def get_operations_copilot(
    memory: Annotated[MemoryClient, Depends(get_memory_client)],
    client: Annotated[AsyncAnthropic, Depends(get_anthropic_client)],
    settings: SettingsDep,
) -> OperationsCopilot:
    return MemoryBackedCopilot(memory=memory, llm=client, model=settings.agent_model)


WarehouseAgentDep = Annotated[WarehouseAgent, Depends(get_warehouse_agent)]
OperationsCopilotDep = Annotated[OperationsCopilot, Depends(get_operations_copilot)]
