"""
Token Usage & Cost Tracking (US-503)

Tracks token consumption per user and department.
Alerts when departments exceed 80% of daily quota.
Uses Redis for transient storage; gracefully degrades on Redis errors.
"""


import json
import logging
from datetime import datetime, timezone
from typing import Dict

from src.secrag.config import settings
from src.secrag.gateway.rate_limiter import redis_client

logger = logging.getLogger(__name__)

# Quota mapping by department
DEPT_QUOTAS = {
    "finance": 500000,
    "hr": 100000,
    "corp": 100000,
    "standard": 50000,
    "public": 50000,
}

ALERT_THRESHOLD_PERCENT = 80


async def record_token_usage(
    user_id: str,
    dept: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
) -> None:
    """
    Record LLM token usage for a query in Redis.

    Stores as JSON line in Redis list keyed by department and date.
    Example key: `usage:finance:2026-03-31`

    Args:
        user_id: User identifier
        dept: Department code
        tokens_input: Tokens in prompt
        tokens_output: Tokens in response
        cost_usd: Cost in USD
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"usage:{dept}:{today}"

        usage_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "department": dept,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "total_tokens": tokens_input + tokens_output,
            "cost_usd": cost_usd,
        }

        # Append to Redis list
        await redis_client.rpush(key, json.dumps(usage_record))

        # Trim to last 10K entries (prevents unbounded growth)
        await redis_client.ltrim(key, -10000, -1)

        # Set TTL to 48 hours (covers full day + margin)
        await redis_client.expire(key, 172800)

        logger.debug(f"Recorded usage: {dept} ({tokens_input + tokens_output} tokens)")

    except Exception as e:
        # Fail-open: log but don't raise (cost tracking mustn't break requests)
        logger.warning(f"Failed to record token usage: {e}")


async def get_daily_usage(dept: str) -> Dict[str, int | float]:
    """
    Get today's token usage for a department from Redis.

    Returns:
        {
            "dept": str,
            "tokens_used": int,
            "quota": int,
            "percent_used": float (0-100),
            "alert_triggered": bool (if >= 80%),
        }
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"usage:{dept}:{today}"
        quota = DEPT_QUOTAS.get(dept, 50000)

        # Get all usage records for today
        records = await redis_client.lrange(key, 0, -1)

        tokens_used = 0
        for record_json in records:
            try:
                record = json.loads(record_json)
                tokens_used += record.get("total_tokens", 0)
            except json.JSONDecodeError:
                continue

        percent_used = (tokens_used / quota * 100) if quota > 0 else 0
        alert_triggered = percent_used >= ALERT_THRESHOLD_PERCENT

        return {
            "dept": dept,
            "tokens_used": tokens_used,
            "quota": quota,
            "percent_used": round(percent_used, 2),
            "alert_triggered": alert_triggered,
        }

    except Exception as e:
        logger.warning(f"Failed to get daily usage for {dept}: {e}")
        # Return default (safe) response on error
        return {
            "dept": dept,
            "tokens_used": 0,
            "quota": DEPT_QUOTAS.get(dept, 50000),
            "percent_used": 0.0,
            "alert_triggered": False,
        }


async def check_dept_quota_alert(dept: str) -> bool:
    """
    Check if department exceeded 80% of daily quota.

    Args:
        dept: Department code

    Returns:
        True if alert should be sent
    """
    try:
        usage = await get_daily_usage(dept)
        return usage["alert_triggered"]
    except Exception as e:
        logger.error(f"Failed to check quota alert for {dept}: {e}")
        return False


async def send_cost_alert(
    dept: str,
    tokens_used: int,
    quota: int,
    channel: str = "slack",
) -> None:
    """
    Send alert when department quota approaching.

    Supports Slack webhook (if configured) or logs as WARNING.

    Args:
        dept: Department code
        tokens_used: Tokens consumed today
        quota: Daily token quota
        channel: Alert channel (slack, email, etc.)
    """
    try:
        percent = (tokens_used / quota * 100) if quota > 0 else 0
        message = f"🚨 {dept} department at {percent:.1f}% of daily token quota: {tokens_used} / {quota} tokens used. Quota reset at midnight UTC."  # noqa: E501

        if channel == "slack" and settings.slack_webhook_url:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    await client.post(settings.slack_webhook_url, json={"text": message})
                logger.info(f"Slack alert sent for {dept}")
            except Exception as e:
                logger.warning(f"Failed to send Slack alert: {e}")
        else:
            # Fallback to logging
            logger.warning(message)

    except Exception as e:
        logger.error(f"Error in send_cost_alert: {e}")
