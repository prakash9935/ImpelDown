"""
Rate Limiting & Quota Enforcement (US-304, Sprint 3)

Redis-backed sliding window rate limiting and daily token quotas.

Implements:
  - check_rate_limit() — 10 req/min per user
  - check_quota() — daily token limits per user and department
  - increment_usage() — track usage after request
"""

import logging

from datetime import datetime, timezone
from typing import Tuple

import redis.asyncio

from src.secrag.config import settings

logger = logging.getLogger(__name__)

# Token quotas (per day)
QUOTA_LIMITS = {
    "user": settings.rate_limit_tokens_per_day,  # 100K
    "finance": settings.dept_finance_quota,  # 500K
    "hr": settings.dept_hr_quota,  # 100K
    "standard": settings.dept_standard_quota,  # 50K
    "public": settings.dept_standard_quota,  # Same as standard
    "corp": settings.dept_finance_quota,  # Same as finance
}

# Max requests per minute
MAX_REQUESTS_PER_MINUTE = settings.rate_limit_per_minute  # 10

# SECURITY H-04: Circuit breaker for fail-closed behavior
_REDIS_FAILURE_COUNT = 0
_CIRCUIT_BREAKER_THRESHOLD = 5
_CIRCUIT_BROKEN = False


async def _get_redis_client() -> redis.asyncio.Redis:
    """Get Redis client from URL."""
    return await redis.asyncio.from_url(settings.redis_url)


async def check_rate_limit(user_id: str) -> bool:
    """
    Check if user has exceeded 10 requests per minute (US-304).

    Uses Redis sliding window with 60-second TTL.
    SECURITY H-04: Implements circuit breaker for fail-closed behavior.

    Args:
        user_id: Unique user identifier

    Returns:
        True if allowed, False if rate limited
    """
    global _REDIS_FAILURE_COUNT, _CIRCUIT_BROKEN

    # Check circuit breaker first
    if _CIRCUIT_BROKEN:
        logger.warning(f"Circuit breaker open: denying request for {user_id}")
        return False  # Fail closed

    try:
        redis_client = await _get_redis_client()
        key = f"ratelimit:{user_id}:minute"

        # Increment counter
        count = await redis_client.incr(key)

        # Set expiry on first request
        if count == 1:
            await redis_client.expire(key, 60)

        allowed = count <= MAX_REQUESTS_PER_MINUTE

        if not allowed:
            logger.warning(f"Rate limit exceeded for user {user_id}: {count} requests")
        else:
            logger.debug(
                f"Rate limit check passed for user {user_id}: {count}/{MAX_REQUESTS_PER_MINUTE}"
            )

        _REDIS_FAILURE_COUNT = 0  # Reset on success
        await redis_client.close()
        return allowed

    except Exception as e:
        logger.error(f"Rate limit check failed for user {user_id}: {e}")
        _REDIS_FAILURE_COUNT += 1

        if _REDIS_FAILURE_COUNT >= _CIRCUIT_BREAKER_THRESHOLD:
            _CIRCUIT_BROKEN = True
            logger.critical(
                f"Circuit breaker OPEN: {_REDIS_FAILURE_COUNT} consecutive Redis failures. "
                "Rate limiting disabled (fail-closed)."
            )

        return False  # Fail closed instead of open


async def check_quota(user_id: str, dept: str, tokens_used: int) -> Tuple[bool, str]:
    """
    Check if user/department has tokens remaining today (US-304).

    Verifies both user and department quotas.
    SECURITY H-04: Fails closed when Redis is unavailable.

    Args:
        user_id: User identifier
        dept: User's department
        tokens_used: Tokens to consume

    Returns:
        (is_allowed: bool, message: str)
    """
    global _REDIS_FAILURE_COUNT, _CIRCUIT_BROKEN

    # Check circuit breaker first
    if _CIRCUIT_BROKEN:
        logger.warning(f"Circuit breaker open: denying quota check for {user_id}")
        return False, "Service unavailable (circuit breaker open)"

    try:
        redis_client = await _get_redis_client()

        # Get user quota
        user_key = f"user_quota:{user_id}:day"
        user_used = await redis_client.get(user_key)
        user_used = int(user_used) if user_used else 0
        user_limit = QUOTA_LIMITS["user"]

        if user_used + tokens_used > user_limit:
            logger.warning(
                f"User quota exceeded for {user_id}: {user_used + tokens_used} > {user_limit}"
            )
            await redis_client.close()
            return False, f"User daily quota exceeded: {user_used}/{user_limit} tokens used"

        # Get department quota
        dept_key = f"dept_quota:{dept}:day"
        dept_used = await redis_client.get(dept_key)
        dept_used = int(dept_used) if dept_used else 0
        dept_limit = QUOTA_LIMITS.get(dept, QUOTA_LIMITS["standard"])

        if dept_used + tokens_used > dept_limit:
            logger.warning(
                f"Department quota exceeded for {dept}: {dept_used + tokens_used} > {dept_limit}"
            )
            await redis_client.close()
            return False, f"Department daily quota exceeded: {dept_used}/{dept_limit} tokens used"

        _REDIS_FAILURE_COUNT = 0  # Reset on success
        await redis_client.close()
        logger.debug(
            f"Quota check passed for user {user_id} ({user_used}/{user_limit}) and dept {dept} ({dept_used}/{dept_limit})"  # noqa: E501
        )
        return True, "Quota available"

    except Exception as e:
        logger.error(f"Quota check failed for user {user_id}: {e}")
        _REDIS_FAILURE_COUNT += 1

        if _REDIS_FAILURE_COUNT >= _CIRCUIT_BREAKER_THRESHOLD:
            _CIRCUIT_BROKEN = True
            logger.critical(
                f"Circuit breaker OPEN: {_REDIS_FAILURE_COUNT} consecutive Redis failures. "
                "Quota enforcement disabled (fail-closed)."
            )

        return False, "Quota check error (service unavailable)"  # Fail closed


async def increment_usage(user_id: str, dept: str, tokens_used: int) -> None:
    """
    Record token usage against user and department quotas (US-304).

    Updates Redis counters with TTL until next midnight UTC.

    Args:
        user_id: User identifier
        dept: Department code
        tokens_used: Number of tokens consumed
    """
    try:
        redis_client = await _get_redis_client()

        # Calculate seconds until midnight UTC
        now = datetime.now(timezone.utc)
        midnight = (now + __import__("datetime").timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        ttl = int((midnight - now).total_seconds())

        # Increment user quota
        user_key = f"user_quota:{user_id}:day"
        await redis_client.incrby(user_key, tokens_used)
        await redis_client.expire(user_key, ttl)

        # Increment department quota
        dept_key = f"dept_quota:{dept}:day"
        await redis_client.incrby(dept_key, tokens_used)
        await redis_client.expire(dept_key, ttl)

        logger.debug(
            f"Usage recorded: user={user_id} (+{tokens_used}), dept={dept} (+{tokens_used})"
        )

        await redis_client.close()

    except Exception as e:
        logger.error(f"Failed to increment usage for user {user_id}: {e}")
