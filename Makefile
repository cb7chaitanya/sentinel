.PHONY: install test lint format up down logs web

SERVICES := apps/gateway services/ingestion services/vision services/events services/memory services/agent

install:
	uv sync --all-packages
	cd apps/web && npm install

test:
	# Run separately: every service has its own tests/__init__.py, and
	# pytest resolves them all to the same top-level "tests" module name
	# if given multiple service directories in one invocation.
	uv run pytest libs/sentinel_common
	for service in $(SERVICES); do uv run pytest $$service || exit 1; done

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
