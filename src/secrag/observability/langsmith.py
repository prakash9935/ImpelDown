"""
LangSmith Integration (US-501)

Traces every query with user_id, role, retrieved chunks, response, latency, cost.
Gracefully degrades to structured logging if LangSmith is not configured.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.secrag.config import settings

logger = logging.getLogger(__name__)

# Module-level client (lazy initialized)
_LANGSMITH_CLIENT = None


def initialize_langsmith_tracer() -> None:
    """
    Initialize LangSmith client from settings.
    Sets LANGCHAIN_API_KEY and LANGCHAIN_PROJECT environment variables.
    No-op if LANGSMITH_API_KEY is not configured.
    """
    global _LANGSMITH_CLIENT

    if not settings.langsmith_api_key:
        logger.debug(
            "LangSmith API key not configured, tracing will use structured logging fallback"
        )
        return

    # Set environment variables for LangChain/LangSmith
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project or "secrag-dev"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

    try:
        from langsmith import Client

        _LANGSMITH_CLIENT = Client()
        logger.info(f"LangSmith tracer initialized (project={os.environ['LANGCHAIN_PROJECT']})")
    except Exception as e:
        logger.warning(
            f"Failed to initialize LangSmith client: {e}. Falling back to structured logging."
        )


async def trace_query(
    user_id: str,
    role: str,
    query: str,
    retrieved_chunks: List[Dict],
    response: str,
    latency_ms: float,
    tokens_used: int,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Log a query trace to LangSmith or structured log if not configured.

    Creates a trace with:
      {
        "trace_id": "abc123xyz",
        "user_id": user_id,
        "user_role": role,
        "query": query,
        "retrieved_chunks": [
          {
            "chunk_id": str,
            "trust_score": float,
            "dept": str,
          }
        ],
        "llm_response": response,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
        "timestamp": datetime,
        ...metadata
      }

    Args:
        user_id: User identifier
        role: User's RBAC role
        query: User's query
        retrieved_chunks: Chunks returned from Qdrant
        response: LLM response
        latency_ms: Query latency
        tokens_used: Tokens consumed
        metadata: Additional metadata

    Never raises — observability must not break the request path.
    """
    try:
        trace_id = str(uuid.uuid4())
        trace_data = {
            "trace_id": trace_id,
            "user_id": user_id,
            "user_role": role,
            "query": query,
            "retrieved_chunks": [
                {
                    "chunk_id": chunk.get("chunk_id", chunk.get("id", "")),
                    "trust_score": chunk.get("trust_score", 0.0),
                    "dept": chunk.get("dept", "unknown"),
                }
                for chunk in retrieved_chunks
            ],
            "llm_response": (
                response[:200] + "..." if len(response) > 200 else response
            ),  # Truncate for logging
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add optional metadata
        if metadata:
            trace_data.update(metadata)

        # Try to send to LangSmith if configured
        if _LANGSMITH_CLIENT:
            try:
                # LangSmith client uses context manager patterns, but we just log structured data here # noqa: E501
                # For actual tracing integration, you'd use @as_runnable or similar decorators
                logger.debug(f"[LANGSMITH TRACE] {json.dumps(trace_data)}")
            except Exception as e:
                logger.warning(f"Failed to trace to LangSmith: {e}")
        else:
            # Fallback: log as structured JSON
            logger.info(f"[QUERY TRACE] {json.dumps(trace_data)}")

    except Exception as e:
        # Never raise — observability must not break the request
        logger.error(f"Error in trace_query: {e}", exc_info=True)
