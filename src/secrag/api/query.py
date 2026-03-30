"""
Query Endpoint (POST /api/v1/query)

Submit a question and get a RAG response with RBAC filtering and guardrails.

Auth: OIDC JWT required (set by AuthMiddleware)
Rate Limit: 10 req/min per user (checked by RateLimitMiddleware)
Jailbreak: Detected by JailbreakMiddleware
Security: RBAC filtering, LlamaGuard classification, PII redaction

Orchestrates: embed → retrieve (RBAC) → prompt → LLM → guardrails → respond
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.secrag.inference.pipeline import infer_response
from src.secrag.retrieval.retriever import embed_text

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    """User query request."""

    query: str
    top_k: int = 5  # Number of chunks to retrieve


class QueryResponse(BaseModel):
    """Query response with metadata."""

    response: str
    chunks_used: List[str]
    latency_ms: float
    tokens_used: int
    is_safe: bool
    pii_redacted: bool


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    http_request: Request,
) -> QueryResponse:
    """
    Submit a question and get a RAG response.

    Security flow:
      - AuthMiddleware: validates JWT, sets request.state.user_id + request.state.role
      - JailbreakMiddleware: checks query for jailbreak patterns (returns 403 if detected)
      - RateLimitMiddleware: checks rate limit before processing (returns 429 if exceeded)
      - This endpoint: embeds query, calls inference pipeline

    Args:
        request: Query request body (query, top_k)
        http_request: FastAPI request object (context from middleware)

    Returns:
        QueryResponse with response text, chunks used, safety flags, latency

    Raises:
        HTTPException(400): Invalid request
        HTTPException(403): Jailbreak detected (via middleware)
        HTTPException(429): Rate limit exceeded (via middleware)
    """
    # Extract user context from middleware (set by AuthMiddleware)
    user_id = getattr(http_request.state, "user_id", None)
    role = getattr(http_request.state, "role", None)

    if not user_id or not role:
        logger.error("Missing user context in request state (AuthMiddleware not executed?)")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validate request
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if request.top_k < 1 or request.top_k > 20:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 20")

    logger.info(f"Query received from user {user_id} (role={role}): {request.query[:100]}...")

    try:
        # Embed query (384-dimensional embedding)
        query_embedding = embed_text(request.query)
        logger.debug(f"Query embedded (dim={len(query_embedding)})")

        # Call inference pipeline
        # Pipeline orchestrates: retrieve → prompt → LLM → guardrails
        result = await infer_response(
            query=request.query,
            user_id=user_id,
            role=role,
            query_embedding=query_embedding,
        )

        logger.info(
            f"Query processed successfully for user {user_id}: {result['latency_ms']:.2f}ms"
        )

        return QueryResponse(
            response=result["response"],
            chunks_used=result["chunks_used"],
            latency_ms=result["latency_ms"],
            tokens_used=result["tokens_used"],
            is_safe=result["is_safe"],
            pii_redacted=result["pii_redacted"],
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Query processing failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Query processing failed")
