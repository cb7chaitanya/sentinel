# Build context must be the monorepo root, e.g.
#   docker build -f services/vision/Dockerfile -t sentinel-vision .
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /app

FROM base AS builder
COPY pyproject.toml uv.lock* /app/
COPY libs/sentinel_common /app/libs/sentinel_common
COPY services/vision /app/services/vision
WORKDIR /app/services/vision
RUN uv sync --frozen --no-dev --no-editable || uv sync --no-dev --no-editable

FROM base AS runtime
RUN useradd --create-home --uid 1000 sentinel
COPY --from=builder /app/services/vision /app/services/vision
COPY --from=builder /app/libs/sentinel_common /app/libs/sentinel_common
WORKDIR /app/services/vision
ENV PATH="/app/services/vision/.venv/bin:$PATH"
USER sentinel

EXPOSE 8002
CMD ["uvicorn", "vision.main:app", "--host", "0.0.0.0", "--port", "8002"]
