# Build context must be the monorepo root, e.g.
#   docker build -f services/agent/Dockerfile -t sentinel-agent .
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv
WORKDIR /app

FROM base AS builder
COPY pyproject.toml uv.lock* /app/
COPY libs/sentinel_common /app/libs/sentinel_common
COPY services/agent /app/services/agent
WORKDIR /app/services/agent
RUN uv sync --frozen --no-dev --no-editable || uv sync --no-dev --no-editable

FROM base AS runtime
RUN useradd --create-home --uid 1000 sentinel
COPY --from=builder /app/services/agent /app/services/agent
COPY --from=builder /app/libs/sentinel_common /app/libs/sentinel_common
WORKDIR /app/services/agent
ENV PATH="/app/services/agent/.venv/bin:$PATH"
USER sentinel

EXPOSE 8005
CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8005"]
