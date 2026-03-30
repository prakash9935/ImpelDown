"""
Health Check Endpoint (GET /api/v1/health)

Simple liveness probe for K8s, load balancers.

Checks Qdrant and Redis connectivity. Returns:
  - 200 {"status": "ok"} if all healthy
  - 200 {"status": "degraded", ...} if partial failure
  - 503 if critical service (Qdrant) down
"""

import logging
from typing import Dict

import redis.asyncio
from fastapi import APIRouter, HTTPException

from src.secrag.config import settings
from src.secrag.retrieval.qdrant_client import QdrantVectorDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Verifies:
      - Qdrant vector database connectivity (critical)
      - Redis cache connectivity

    Returns:
        {"status": "ok", "qdrant": "ok", "redis": "ok"} if all healthy
        {"status": "degraded", ...} if partial failure (Qdrant still up)
        Raises HTTPException(503) if Qdrant is down

    Critical services (failure → 503):
      - Qdrant (vector DB required for retrieval)

    Degraded services (failure → 200 with "degraded"):
      - Redis (caching, rate limiting — fallback available)
    """
    status_dict = {"status": "ok"}
    is_degraded = False

    # Check Qdrant (critical)
    try:
        qdrant = QdrantVectorDB(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
        )
        qdrant.health_check()
        status_dict["qdrant"] = "ok"
        logger.debug("Qdrant health check passed")
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database unavailable")

    # Check Redis (degraded if fails)
    try:
        redis_client = await redis.asyncio.from_url(settings.redis_url)
        await redis_client.ping()
        status_dict["redis"] = "ok"
        await redis_client.close()
        logger.debug("Redis health check passed")
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        status_dict["redis"] = "degraded"
        is_degraded = True

    if is_degraded:
        status_dict["status"] = "degraded"

    return status_dict
