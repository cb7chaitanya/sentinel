# Sentinel

AI-native warehouse monitoring platform. Watches RTSP cameras, extracts
structured warehouse events, persists them as memory, and exposes AI agents
that reason over warehouse operations.

No business logic is implemented yet — this repo is a bootstrap: folder
structure, typed configuration, dependency injection wiring, logging, and
Docker support for every service.

## Layout

```
apps/                   deployable applications (things with an entrypoint)
  gateway/               FastAPI BFF — composes internal services for the frontend
  web/                   Next.js + TypeScript + Tailwind frontend

services/                independently testable domain services
  ingestion/              captures RTSP camera streams
  vision/                 YOLO object detection/tracking over frames
  events/                 derives warehouse events from detections
  memory/                 persists structured memory in PostgreSQL (SQLAlchemy + Alembic)
  agent/                  AI agents reasoning over warehouse memory (Anthropic)

libs/
  sentinel_common/        shared config, logging, DI, DB, and Pydantic schemas

infra/
  postgres/               DB bootstrap SQL

docker-compose.yml        local orchestration of every service + Postgres
```

Every Python package (`apps/gateway`, each `services/*`, `libs/sentinel_common`)
is a standalone `uv` workspace member with its own `pyproject.toml`, `tests/`,
and `Dockerfile` — each is independently installable, testable, and
deployable.

## Architecture conventions

Each service follows the same internal shape:

```
src/<service>/
  main.py            FastAPI app factory (create_app)
  core/
    config.py         Settings (pydantic-settings), extends BaseServiceSettings
    di.py             composition root — typed provider functions wired via Depends()
  domain/              Protocol interfaces (no framework/infra imports)
  infra/               concrete adapters implementing domain Protocols
  api/v1/              routers, request/response handling only
tests/
```

- **Strong typing**: Pydantic v2 models everywhere at service boundaries, `Protocol`
  interfaces for domain contracts, strict mypy/pyright config at the workspace root.
- **Dependency injection**: no DI framework — typed provider functions in each
  service's `core/di.py`, wired through FastAPI's native `Depends()`. Business
  logic depends on `domain` Protocols, never directly on `infra` adapters.
- **Logging**: `sentinel_common.logging.configure_logging()` sets up structured
  JSON logs (or human-readable in local dev) for every service at startup.
- **Config**: `sentinel_common.config.BaseServiceSettings` (pydantic-settings) is
  subclassed per service; every value is overridable via env vars or `.env`.

## Local development

```bash
make install   # uv sync (Python workspace) + npm install (web)
make test      # run every service's test suite
make lint      # ruff + eslint
make up        # docker compose up --build (all services + Postgres)
make web       # run the Next.js dev server directly
```

Each service also runs standalone, e.g.:

```bash
cd services/vision
uv run uvicorn vision.main:app --reload --port 8002
uv run pytest
```
