"""
SecRAG FastAPI Application Entrypoint

Initializes the FastAPI app, registers middleware stack, and includes all route handlers.

Middleware execution order (last added = outermost):
  1. LoggingMiddleware (outermost) — structured logging of all requests/responses
  2. AuthMiddleware — JWT extraction + validation
  3. JailbreakMiddleware — prompt injection detection
  4. RateLimitMiddleware (innermost) — sliding window rate limiting

Security flow:
  Request → Logging → Auth (JWT) → Jailbreak Check → Rate Limit → Handler
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from src.secrag.api import health, ingest, query
from src.secrag.config import settings
from src.secrag.gateway.middleware import (
    AuthMiddleware,
    JailbreakMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
)

# Initialize observability
try:
    from src.secrag.observability.langsmith import initialize_langsmith_tracer

    _init_langsmith = True
except ImportError:
    _init_langsmith = False

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Secure Retrieval-Augmented Generation with RBAC & Poisoning Defense",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
)


# CORS configuration for frontend access
# SECURITY H-01: Do not use wildcard origins with credentials
cors_origins = (
    settings.cors_origins.split(",")
    if hasattr(settings, "cors_origins") and settings.cors_origins
    else []  # Empty list requires explicit configuration
)

if not cors_origins and not settings.debug:
    logger.critical(
        "❌ FATAL: CORS_ORIGINS not configured. "
        "Cannot start in production without explicit CORS origins. "
        "Set CORS_ORIGINS env var or DEBUG=True for development."
    )
    raise RuntimeError("CORS origins not configured")

# Middleware stack (order matters — last added = outermost)
# Execution flow: CORS → Logging → Auth → Jailbreak → RateLimit → Handler
app.add_middleware(RateLimitMiddleware)  # Innermost: rate limit after auth
app.add_middleware(JailbreakMiddleware)  # Jailbreak detection on query
app.add_middleware(AuthMiddleware)  # JWT validation and role extraction
app.add_middleware(LoggingMiddleware)  # Structured logging
app.add_middleware(
    CORSMiddleware,  # Outermost: must handle OPTIONS preflight before auth
    allow_origins=cors_origins or ["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup."""
    # SECURITY C-01: Prevent TESTING=True in production
    if settings.testing and not settings.debug:
        logger.critical(
            "❌ FATAL: TESTING=True in production mode. "
            "This disables JWT signature verification. Set TESTING=False."
        )
        raise RuntimeError(
            "Cannot start: TESTING=True is a development-only mode. "
            "Set TESTING=False before deploying to production."
        )

    if settings.testing:
        logger.warning(
            "⚠️  TESTING MODE ENABLED: JWT signature verification is disabled. "
            "All tokens will be accepted without validation. "
            "This is only safe for local development."
        )

    logger.info(f"🚀 {settings.app_name} v{settings.app_version} starting up...")
    logger.info(f"  API: {settings.api_host}:{settings.api_port}{settings.api_v1_prefix}")

    # SECURITY H-05: Mask passwords in logs
    def mask_url(url: str) -> str:
        """Mask passwords in connection strings."""
        if "@" in url:
            prefix, rest = url.split("@", 1)
            return prefix.rsplit("//", 1)[0] + "://" + "***@" + rest
        return url

    logger.info(f"  Qdrant: {mask_url(settings.qdrant_url)}")
    logger.info(f"  Redis: {mask_url(settings.redis_url)}")
    logger.info(f"  LLM: {settings.groq_model}")
    logger.info(f"  Debug mode: {settings.debug}")

    # Initialize observability
    if _init_langsmith:
        try:
            initialize_langsmith_tracer()
            logger.info("  LangSmith tracing initialized")
        except Exception as e:
            logger.warning(f"LangSmith initialization failed: {e}")

    # Pre-load embedding model to avoid blocking on first request
    try:
        from src.secrag.retrieval.retriever import _get_embedding_model

        logger.info(f"  Pre-loading embedding model: {settings.embedding_model}")
        _get_embedding_model()
        logger.info("  ✅ Embedding model loaded")
    except Exception as e:
        logger.error(f"Failed to pre-load embedding model: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    logger.info(f"🛑 {settings.app_name} shutting down...")


# Include API routers
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["Health"])
app.include_router(query.router, prefix=settings.api_v1_prefix, tags=["Query"])
app.include_router(ingest.router, prefix=settings.api_v1_prefix, tags=["Ingest"])

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Global exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle uncaught exceptions with structured logging."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
