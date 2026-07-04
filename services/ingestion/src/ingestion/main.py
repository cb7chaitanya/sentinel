from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sentinel_common.logging import configure_logging

from ingestion.api.v1.router import api_router
from ingestion.core.config import get_settings
from ingestion.core.di import get_stream_registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    registry = get_stream_registry()
    await registry.start()
    try:
        yield
    finally:
        await registry.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level, settings.log_json)

    app = FastAPI(title="Sentinel Ingestion Service", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
