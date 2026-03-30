"""
Prometheus Metrics Collection (US-502)

Exposes metrics via /metrics endpoint for Prometheus scraping.
Tracks query volume, latency, jailbreak blocks, PII redaction, and active users.
"""

import logging

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Counters — increment-only metrics
query_total = Counter(
    "secrag_queries_total",
    "Total number of queries processed",
    ["status", "user_role"],
)

jailbreak_blocked_total = Counter(
    "secrag_jailbreaks_blocked_total",
    "Total number of jailbreak attempts blocked",
    ["detection_layer"],  # "keyword", "base64", "rot13", "sanitizer"
)

pii_redacted_total = Counter(
    "secrag_pii_redacted_total",
    "Total PII items redacted",
    ["type"],  # "ssn", "email", "phone"
)

ingest_total = Counter(
    "secrag_ingest_total",
    "Total documents ingested",
    ["status"],  # "success", "failure"
)

# Histograms — track distribution of values
query_latency_seconds = Histogram(
    "secrag_query_latency_seconds",
    "Query latency in seconds",
    ["step"],  # "retrieve", "prompt", "llm", "classify", "redact", "total"
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

jailbreak_detection_latency_seconds = Histogram(
    "secrag_jailbreak_detection_latency_seconds",
    "Jailbreak detection latency in seconds",
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01),
)

pii_redaction_latency_seconds = Histogram(
    "secrag_pii_redaction_latency_seconds",
    "PII redaction latency in seconds",
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01),
)

tokens_used = Histogram(
    "secrag_tokens_used",
    "Tokens used per query (input + output)",
    buckets=(100, 200, 500, 1000, 2000, 5000),
)

# Gauges — can go up or down
active_users_gauge = Gauge(
    "secrag_active_users",
    "Number of active users",
    ["role"],  # "admin", "finance", "hr", "standard"
)

redis_errors_total = Counter(
    "secrag_redis_errors_total",
    "Total Redis connection errors",
)

qdrant_errors_total = Counter(
    "secrag_qdrant_errors_total",
    "Total Qdrant connection errors",
)

llm_errors_total = Counter(
    "secrag_llm_errors_total",
    "Total LLM API errors",
)

cache_hits_total = Counter(
    "secrag_cache_hits_total",
    "Total semantic cache hits",
)

cache_misses_total = Counter(
    "secrag_cache_misses_total",
    "Total semantic cache misses",
)


def increment_query_total(status: str, user_role: str) -> None:
    """Increment query counter."""
    try:
        query_total.labels(status=status, user_role=user_role).inc()
    except Exception as e:
        logger.warning(f"Failed to increment query counter: {e}")


def increment_jailbreak_blocked(detection_layer: str) -> None:
    """Increment jailbreak counter."""
    try:
        jailbreak_blocked_total.labels(detection_layer=detection_layer).inc()
    except Exception as e:
        logger.warning(f"Failed to increment jailbreak counter: {e}")


def increment_pii_redacted(pii_type: str, count: int = 1) -> None:
    """Increment PII redaction counter."""
    try:
        pii_redacted_total.labels(type=pii_type).inc(count)
    except Exception as e:
        logger.warning(f"Failed to increment PII counter: {e}")


def record_query_latency(step: str, latency_seconds: float) -> None:
    """Record query latency histogram."""
    try:
        query_latency_seconds.labels(step=step).observe(latency_seconds)
    except Exception as e:
        logger.warning(f"Failed to record query latency: {e}")


def record_jailbreak_latency(latency_seconds: float) -> None:
    """Record jailbreak detection latency."""
    try:
        jailbreak_detection_latency_seconds.observe(latency_seconds)
    except Exception as e:
        logger.warning(f"Failed to record jailbreak latency: {e}")


def record_pii_latency(latency_seconds: float) -> None:
    """Record PII redaction latency."""
    try:
        pii_redaction_latency_seconds.observe(latency_seconds)
    except Exception as e:
        logger.warning(f"Failed to record PII latency: {e}")


def record_tokens_used(token_count: int) -> None:
    """Record token usage histogram."""
    try:
        tokens_used.observe(token_count)
    except Exception as e:
        logger.warning(f"Failed to record tokens used: {e}")


def set_active_users(user_role: str, count: int) -> None:
    """Set active users gauge."""
    try:
        active_users_gauge.labels(role=user_role).set(count)
    except Exception as e:
        logger.warning(f"Failed to set active users gauge: {e}")


def increment_redis_errors() -> None:
    """Increment Redis error counter."""
    try:
        redis_errors_total.inc()
    except Exception as e:
        logger.warning(f"Failed to increment Redis error counter: {e}")


def increment_qdrant_errors() -> None:
    """Increment Qdrant error counter."""
    try:
        qdrant_errors_total.inc()
    except Exception as e:
        logger.warning(f"Failed to increment Qdrant error counter: {e}")


def increment_llm_errors() -> None:
    """Increment LLM error counter."""
    try:
        llm_errors_total.inc()
    except Exception as e:
        logger.warning(f"Failed to increment LLM error counter: {e}")


def increment_cache_hits() -> None:
    """Increment cache hit counter."""
    try:
        cache_hits_total.inc()
    except Exception as e:
        logger.warning(f"Failed to increment cache hit counter: {e}")


def increment_cache_misses() -> None:
    """Increment cache miss counter."""
    try:
        cache_misses_total.inc()
    except Exception as e:
        logger.warning(f"Failed to increment cache miss counter: {e}")
