"""
Semantic Cache Module (US-504, US-505)

Caches responses based on query embedding similarity.
TTL 24h + event-driven purge on re-ingestion.

Uses Redis for storage. Cache hits when embedding similarity > 0.95.
Gracefully degrades on Redis errors (fail-open).
"""

import hashlib
import json
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional

from src.secrag.gateway.rate_limiter import redis_client
from src.secrag.observability.metrics import increment_cache_hits, increment_cache_misses

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.95
DEFAULT_TTL_SECONDS = 86400  # 24 hours


def hash_embedding(embedding: List[float]) -> str:
    """Hash embedding to cache key (first 16 chars of SHA256)."""
    return hashlib.sha256(str(embedding).encode()).hexdigest()[:16]


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    try:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)
    except Exception as e:
        logger.warning(f"Error computing cosine similarity: {e}")
        return 0.0


async def get_cached_response(
    query_embedding: List[float],
    user_role: str = None,  # SECURITY M-07: Include role in cache lookup
) -> Optional[Dict]:
    """
    Retrieve cached response for similar query via embedding similarity.

    Steps:
      1. Hash query embedding
      2. Try exact-hash lookup in Redis
      3. If miss, scan all cache keys and compute cosine similarity
      4. Return first match where similarity > 0.95

    Args:
        query_embedding: Embedding of user's query (384-dim)

    Returns:
        Cached response dict or None if no match
    """
    try:
        query_hash = hash_embedding(query_embedding)

        # Step 1: Try exact-hash lookup (fastest path)
        # SECURITY M-07: Include user role in cache key to prevent privilege escalation
        exact_key = f"cache:{user_role}:{query_hash}" if user_role else f"cache:{query_hash}"
        cached_json = await redis_client.get(exact_key)
        if cached_json:
            try:
                result = json.loads(cached_json)
                logger.debug(f"Cache hit (exact): {query_hash}")
                increment_cache_hits()
                return result
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache key {exact_key}")

        # Step 2: Scan all cache keys for similarity matches (O(n) but acceptable for dev)
        cursor = 0
        scanned_count = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match="cache:*", count=100)
            scanned_count += len(keys)

            for key in keys:
                try:
                    cached_json = await redis_client.get(key)
                    if not cached_json:
                        continue

                    cached_data = json.loads(cached_json)
                    cached_embedding = cached_data.get("_embedding")
                    if not cached_embedding:
                        continue

                    similarity = _cosine_similarity(query_embedding, cached_embedding)
                    if similarity >= SIMILARITY_THRESHOLD:
                        logger.debug(f"Cache hit (similarity={similarity:.3f}): {key}")
                        increment_cache_hits()
                        # Return response without embedding
                        result = {k: v for k, v in cached_data.items() if k != "_embedding"}
                        return result
                except Exception as e:
                    logger.warning(f"Error checking cache key {key}: {e}")
                    continue

            if cursor == 0:
                break

        # No match found
        logger.debug(f"Cache miss: scanned {scanned_count} entries")
        increment_cache_misses()
        return None

    except Exception as e:
        logger.warning(f"Error in get_cached_response: {e}")
        # Fail-open: return None (cache miss) on error
        increment_cache_misses()
        return None


async def cache_response(
    query_embedding: List[float],
    query_text: str,
    response: str,
    chunks_used: List[str],
    doc_ids: Optional[List[str]] = None,
    user_role: str = None,  # SECURITY M-07: Include role in cache key
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    """
    Store response in cache with TTL.

    Key: `cache:{user_role}:{hash(embedding)}`
    Value: JSON with query, response, chunks_used, doc_ids, embedding

    Args:
        query_embedding: Embedding of query (384-dim)
        query_text: Raw query text
        response: LLM response
        chunks_used: Chunk IDs used in response
        doc_ids: Document IDs referenced (for invalidation)
        ttl_seconds: Cache TTL in seconds (default 24h)
    """
    try:
        query_hash = hash_embedding(query_embedding)
        # SECURITY M-07: Include user role in cache key to prevent privilege escalation
        key = f"cache:{user_role}:{query_hash}" if user_role else f"cache:{query_hash}"

        cache_data = {
            "query": query_text,
            "response": response,
            "chunks_used": chunks_used,
            "doc_ids": doc_ids or [],
            "created_at": datetime.utcnow().isoformat(),
            "_embedding": query_embedding,  # Store for similarity matching
        }

        # Store in Redis with TTL
        await redis_client.setex(key, ttl_seconds, json.dumps(cache_data))

        logger.debug(f"Cached response for query (TTL {ttl_seconds}s): {query_hash}")

    except Exception as e:
        logger.warning(f"Error in cache_response: {e}")
        # Fail-open: don't raise, just log
