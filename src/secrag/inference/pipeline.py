"""
Inference Pipeline Orchestrator (Epic 4, Sprint 3)

Coordinates end-to-end query processing:
  1. Retrieve chunks with RBAC filtering
  2. Build XML-delimited prompt with anti-injection rules
  3. Call LLM with temperature=0.0
  4. Check for injected commands in response
  5. Classify response safety (LlamaGuard)
  6. Redact PII
  7. Return response or security violation

Implements:
  - infer_response() — full 6-step orchestration
  - Error handling for each step
  - Latency tracking
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

from src.secrag.inference.guardrails import (
    check_injected_commands,
    classify_response,
    redact_pii,
)
from src.secrag.inference.llm_client import call_llm
from src.secrag.inference.prompt_builder import build_prompt
from src.secrag.retrieval.retriever import retrieve_chunks

# Cache imports
try:
    from src.secrag.cache.semantic_cache import cache_response, get_cached_response

    _cache_enabled = True
except ImportError:
    _cache_enabled = False

    async def get_cached_response(*args, **kwargs):
        return None

    async def cache_response(*args, **kwargs):
        pass


# Observability imports (fail-open if not available)
try:
    from src.secrag.observability.cost_tracker import (
        check_dept_quota_alert,
        get_daily_usage,
        record_token_usage,
        send_cost_alert,
    )
    from src.secrag.observability.langsmith import trace_query
    from src.secrag.observability.metrics import (
        increment_pii_redacted,
        increment_query_total,
        record_query_latency,
        record_tokens_used,
    )
except ImportError:
    # Graceful fallback if observability modules unavailable
    async def trace_query(*args, **kwargs):
        pass

    async def record_token_usage(*args, **kwargs):
        pass

    async def check_dept_quota_alert(*args, **kwargs):
        return False

    async def send_cost_alert(*args, **kwargs):
        pass

    async def get_daily_usage(*args, **kwargs):
        return {}

    def increment_query_total(*args, **kwargs):
        pass

    def increment_pii_redacted(*args, **kwargs):
        pass

    def record_query_latency(*args, **kwargs):
        pass

    def record_tokens_used(*args, **kwargs):
        pass


logger = logging.getLogger(__name__)


async def infer_response(
    query: str,
    user_id: str,
    role: str,
    query_embedding: List[float],
) -> Dict[str, any]:
    """
    End-to-end inference pipeline with guardrails (Epic 4).

    Orchestrates retrieval → prompt building → LLM inference → safety checks → response.

    Args:
        query: User's natural language question
        user_id: User identifier (for audit trail)
        role: User's RBAC role (admin, finance, hr, standard)
        query_embedding: Embedding of query (384-dim)

    Returns:
        {
            "response": str (original or security violation message),
            "chunks_used": List[str] (chunk IDs used for context),
            "is_safe": bool (passed LlamaGuard/safety checks),
            "pii_redacted": bool (if any PII was found and redacted),
            "latency_ms": float,
            "tokens_used": int (estimate),
            "timestamp": datetime,
        }
    """
    start_time = time.time()
    timestamp = datetime.utcnow()

    try:
        # --- Cache Check (before retrieval) ---
        if _cache_enabled:
            try:
                # SECURITY M-07: Pass role to prevent cross-role cache hits
                cached = await get_cached_response(query_embedding, user_role=role)
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"Cache hit! Returned in {latency_ms:.2f}ms")
                    increment_query_total(status="success_cached", user_role=role)
                    record_query_latency(step="cache_hit", latency_seconds=latency_ms / 1000)
                    return {
                        "response": cached.get("response", ""),
                        "chunks_used": cached.get("chunks_used", []),
                        "is_safe": True,
                        "pii_redacted": False,
                        "latency_ms": latency_ms,
                        "tokens_used": len(cached.get("response", "").split()),
                        "timestamp": timestamp,
                        "cache_hit": True,
                    }
            except Exception as e:
                logger.debug(f"Cache lookup failed (non-fatal): {e}")

        # Step 1: Retrieve chunks with RBAC filter
        logger.info(f"Step 1/6: Retrieving chunks for role '{role}'")
        chunks = await retrieve_chunks(query_text=query, role=role, top_k=5)
        logger.info(f"  → Retrieved {len(chunks)} chunks")

        # Step 2: Build XML-delimited prompt
        logger.info("Step 2/6: Building prompt with XML delimiters")
        prompt = build_prompt(query=query, context_chunks=chunks)
        logger.debug(f"  → Prompt length: {len(prompt)} chars")

        # Step 3: Call LLM with temperature=0.0
        logger.info("Step 3/6: Calling LLM")
        response = await call_llm(prompt=prompt, max_tokens=1024)
        logger.debug(f"  → Response length: {len(response)} chars")

        # Step 4: Check for injected commands in response
        logger.info("Step 4/6: Checking for injected commands")
        has_injected = check_injected_commands(response)
        if has_injected:
            logger.warning(f"Injected commands detected in response for user {user_id}")
            return {
                "response": "⚠️ Security violation detected. This incident has been logged.",
                "chunks_used": [c.chunk_id for c in chunks],
                "is_safe": False,
                "pii_redacted": False,
                "latency_ms": (time.time() - start_time) * 1000,
                "tokens_used": len(response.split()),  # Rough estimate
                "timestamp": timestamp,
            }

        # Step 5: Classify response safety via LlamaGuard
        logger.info("Step 5/6: Classifying response safety")
        is_safe, reason = await classify_response(response)
        if not is_safe:
            logger.warning(f"LlamaGuard flagged response for user {user_id}: {reason}")
            return {
                "response": "⚠️ Security violation detected. This incident has been logged.",
                "chunks_used": [c.chunk_id for c in chunks],
                "is_safe": False,
                "pii_redacted": False,
                "latency_ms": (time.time() - start_time) * 1000,
                "tokens_used": len(response.split()),
                "timestamp": timestamp,
            }

        # Step 6: Redact PII
        logger.info("Step 6/6: Redacting PII")
        redacted_response, redaction_log = redact_pii(response)
        pii_redacted = any(redaction_log.values())
        if pii_redacted:
            logger.warning(f"PII redacted from response for user {user_id}: {redaction_log}")

        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Query processed successfully in {latency_ms:.2f}ms")

        # Calculate token counts (input + output)
        tokens_input = len(prompt.split())
        tokens_output = len(response.split())
        tokens_total = tokens_input + tokens_output

        # Extract doc_ids from chunks for cache invalidation tracking
        doc_ids = list(
            set(getattr(c, "source_file", "") for c in chunks if hasattr(c, "source_file"))
        )

        result = {
            "response": redacted_response,
            "chunks_used": [c.chunk_id for c in chunks],
            "is_safe": True,
            "pii_redacted": pii_redacted,
            "latency_ms": latency_ms,
            "tokens_used": tokens_total,
            "timestamp": timestamp,
            "cache_hit": False,
        }

        # --- Cache Storage (fail-open) ---
        if _cache_enabled:
            try:
                # SECURITY M-07: Pass role to prevent cross-role cache pollution
                await cache_response(
                    query_embedding=query_embedding,
                    query_text=query,
                    response=redacted_response,
                    chunks_used=[c.chunk_id for c in chunks],
                    doc_ids=doc_ids,
                    user_role=role,  # Include role in cache key
                    ttl_seconds=86400,  # 24 hours
                )
            except Exception as e:
                logger.debug(f"Failed to cache response: {e}")

        # --- Observability Hooks (fail-open) ---
        try:
            # Record metrics
            increment_query_total(status="success", user_role=role)
            record_query_latency(step="total", latency_seconds=latency_ms / 1000)
            record_tokens_used(tokens_total)

            # Record PII redaction
            if pii_redacted:
                increment_pii_redacted("mixed", count=sum(redaction_log.values()))

            # Trace to LangSmith
            await trace_query(
                user_id=user_id,
                role=role,
                query=query,
                retrieved_chunks=[
                    {
                        "chunk_id": c.chunk_id,
                        "trust_score": c.trust_score,
                        "dept": c.dept,
                    }
                    for c in chunks
                ],
                response=redacted_response,
                latency_ms=latency_ms,
                tokens_used=tokens_total,
                metadata={"pii_redacted": pii_redacted},
            )

            # Record token usage and check quotas
            cost_usd = tokens_total * 0.00001  # Rough estimate (varies by LLM)
            await record_token_usage(
                user_id=user_id,
                dept=role,  # Use role as dept proxy
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
            )

            # Check if department quota exceeded
            if await check_dept_quota_alert(role):
                logger.warning(f"Department {role} quota alert triggered")
                try:
                    usage = await get_daily_usage(role) if "get_daily_usage" in dir() else {}
                    if usage:
                        await send_cost_alert(
                            dept=role,
                            tokens_used=usage.get("tokens_used", 0),
                            quota=usage.get("quota", 0),
                        )
                except Exception as e:
                    logger.warning(f"Failed to send cost alert: {e}")

        except Exception as e:
            # Never raise from observability — log and continue
            logger.warning(f"Observability error in infer_response: {e}")

        return result

    except Exception as e:
        logger.error(f"Inference pipeline failed for user {user_id}: {e}")
        increment_query_total(status="error", user_role=role)
        raise
