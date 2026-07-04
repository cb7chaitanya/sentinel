# Build context must be the monorepo root, e.g.
#   docker build -f services/memory/Dockerfile -t sentinel-memory .
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv
WORKDIR /app

FROM base AS builder
COPY pyproject.toml uv.lock* /app/
COPY libs/sentinel_common /app/libs/sentinel_common
COPY services/memory /app/services/memory
WORKDIR /app/services/memory
RUN uv sync --frozen --no-dev --no-editable || uv sync --no-dev --no-editable

FROM base AS runtime
RUN useradd --create-home --uid 1000 sentinel
COPY --from=builder /app/services/memory /app/services/memory
COPY --from=builder /app/libs/sentinel_common /app/libs/sentinel_common
WORKDIR /app/services/memory
ENV PATH="/app/services/memory/.venv/bin:$PATH"
USER sentinel

EXPOSE 8004
CMD ["uvicorn", "memory.main:app", "--host", "0.0.0.0", "--port", "8004"]
