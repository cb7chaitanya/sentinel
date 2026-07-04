from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.api.v1.router import api_router
from gateway.core.config import get_settings
from sentinel_common.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.service_name, settings.log_level, settings.log_json)

    app = FastAPI(title="Sentinel Gateway", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
