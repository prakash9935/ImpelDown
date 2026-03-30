"""
FastAPI Middleware Integration (Sprint 3)

Wires auth, jailbreak, rate limiting, and logging into FastAPI request/response pipeline.

Execution order (last added = outermost):
  Logging → Auth → Jailbreak → RateLimit → handler

Implements:
  - LoggingMiddleware — structured request/response logging
  - AuthMiddleware — JWT extraction and validation
  - JailbreakMiddleware — jailbreak pattern detection
  - RateLimitMiddleware — sliding window rate limiting
"""

import json
import logging
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.secrag.config import settings
from src.secrag.gateway.auth import extract_role_from_jwt, validate_jwt
from src.secrag.gateway.jailbreak import classify_jailbreak
from src.secrag.gateway.rate_limiter import check_rate_limit, increment_usage

# Audit logging (optional)
try:
    from src.secrag.authorization.audit import log_audit_event

    _audit_enabled = True
except ImportError:
    _audit_enabled = False

    async def log_audit_event(*args, **kwargs):
        pass


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging of all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """
        Log request and response with timing and user context.

        Logs:
        - Request: method, path, user_id, role, timestamp
        - Response: status_code, latency_ms
        """
        start_time = time.time()
        user_id = getattr(request.state, "user_id", "anonymous")
        role = getattr(request.state, "role", "unknown")

        logger.info(f"{request.method} {request.url.path} | user={user_id} role={role}")

        response = await call_next(request)

        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} | status={response.status_code} latency={latency_ms:.2f}ms"  # noqa: E501
        )

        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract and validate JWT from Authorization header."""

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """
        Extract JWT, validate, and extract user role.

        Skips `/api/v1/health` (liveness probe).
        Sets request.state.user_id and request.state.role.
        Returns 401 on failure.
        """
        # Skip health check
        if request.url.path == "/api/v1/health":
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header for {request.url.path}")
            return JSONResponse({"error": "Missing Authorization header"}, status_code=401)

        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid Authorization header format for {request.url.path}")
            return JSONResponse({"error": "Invalid Authorization header"}, status_code=401)

        token = parts[1]

        # Validate JWT
        try:
            claims = await validate_jwt(token)
            user_id = claims.get("sub", "unknown")
            role = extract_role_from_jwt(claims)

            # Store in request state for downstream handlers
            request.state.user_id = user_id
            request.state.role = role
            logger.debug(f"Auth successful: user={user_id} role={role}")

            # Log audit event for authenticated request
            if _audit_enabled:
                try:
                    await log_audit_event(
                        user_id=user_id,
                        role=role,
                        action=request.method,
                        resource=request.url.path,
                        result="authenticated",
                    )
                except Exception as e:
                    logger.debug(f"Audit logging failed: {e}")

        except Exception as e:
            logger.warning(f"JWT validation failed: {e}")
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        return await call_next(request)


class JailbreakMiddleware(BaseHTTPMiddleware):
    """Detect jailbreak attempts in query endpoint."""

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """
        Check POST /api/v1/query for jailbreak patterns.

        Reads request body, checks with classify_jailbreak(), and re-injects body.
        Returns 403 if jailbreak detected.
        """
        # Only check query endpoint
        if request.method == "POST" and request.url.path == "/api/v1/query":
            # Read body (consumes it)
            body = await request.body()

            # Parse JSON
            try:
                query_data = json.loads(body)
                query = query_data.get("query", "")

                # Classify jailbreak
                is_jailbreak, reason = classify_jailbreak(query)

                if is_jailbreak:
                    user_id = getattr(request.state, "user_id", "unknown")
                    logger.warning(f"Jailbreak detected for user {user_id}: {reason}")
                    return JSONResponse(
                        {
                            "error": "Security violation: jailbreak attempt detected",
                            "reason": reason,
                        },
                        status_code=403,
                    )

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in query request")
                return JSONResponse({"error": "Invalid JSON"}, status_code=400)

            # Re-inject body for downstream handlers
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-user rate limits."""

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """
        Check rate limit (10 req/min per user) before processing.

        Only checks API paths (not /docs, /openapi.json, etc.).
        Returns 429 if rate limited.
        """
        # Only check API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # No auth, skip rate limit check
            return await call_next(request)

        # Check rate limit
        allowed = await check_rate_limit(user_id)
        if not allowed:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return JSONResponse(
                {
                    "error": f"Rate limit exceeded: {settings.rate_limit_per_minute} requests per minute"  # noqa: E501
                },
                status_code=429,
            )

        # Call handler and track usage
        response = await call_next(request)

        # Increment usage if successful
        if response.status_code == 200:
            dept = getattr(request.state, "dept", "unknown")
            # Rough token estimate: response body length / 4 (avg 4 chars per token)
            tokens_used = len(response.body) // 4 if hasattr(response, "body") else 100

            try:
                await increment_usage(user_id, dept, tokens_used)
            except Exception as e:
                logger.error(f"Failed to increment usage: {e}")

        return response
