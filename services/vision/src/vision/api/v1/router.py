from fastapi import APIRouter

from vision.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Deliberately no detection endpoints: this service only produces structured
# data (see core/pipeline.py). Callers drive VisionPipeline directly with
# frames rather than over HTTP.
