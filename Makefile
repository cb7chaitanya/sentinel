.PHONY: install test lint format up down logs web

SERVICES := apps/gateway services/ingestion services/vision services/events services/memory services/agent

install:
	uv sync --all-packages
	cd apps/web && npm install

test:
	uv run pytest $(SERVICES) libs/sentinel_common

lint:
	uv run ruff check .
	cd apps/web && npm run lint

format:
	uv run ruff format .

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

web:
	cd apps/web && npm run dev
