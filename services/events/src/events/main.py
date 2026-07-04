from fastapi import FastAPI

from events.api.v1.router import api_router
from events.core.config import get_settings
from sentinel_common.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level, settings.log_json)

    app = FastAPI(title="Sentinel Events Service", version="0.1.0")
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
