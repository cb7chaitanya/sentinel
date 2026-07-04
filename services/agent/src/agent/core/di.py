"""Composition root for the agent service's dependencies."""

from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends

from agent.core.config import Settings, get_settings
from agent.domain.agent import WarehouseAgent
from agent.infra.llm_client import AnthropicWarehouseAgent
from sentinel_common.di import singleton

SettingsDep = Annotated[Settings, Depends(get_settings)]


@singleton
def get_anthropic_client() -> AsyncAnthropic:
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def get_warehouse_agent(
    client: Annotated[AsyncAnthropic, Depends(get_anthropic_client)],
    settings: SettingsDep,
) -> WarehouseAgent:
    return AnthropicWarehouseAgent(client=client, model=settings.agent_model)


WarehouseAgentDep = Annotated[WarehouseAgent, Depends(get_warehouse_agent)]
