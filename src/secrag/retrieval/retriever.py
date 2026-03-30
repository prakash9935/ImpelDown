"""
RBAC-Enforced Vector Retriever (US-201, US-202, US-203, Sprint 2)

Queries Qdrant with role-based payload filters.
Returns top-k chunks authorized for the user's role.

Implements:
  - embed_text(text) -> embedding using sentence-transformers
  - retrieve_chunks(query_text, role, top_k) -> List[RetrievedChunk]
  - RBAC filter applied BEFORE vector search (pre-retrieval, security-critical)
"""

import logging
from dataclasses import dataclass
from typing import List

from sentence_transformers import SentenceTransformer

from src.secrag.config import settings
from src.secrag.retrieval.qdrant_client import QdrantVectorDB
from src.secrag.retrieval.rbac_filter import get_filter_for_role

logger = logging.getLogger(__name__)

# Lazy-loaded embedding model
_EMBEDDING_MODEL = None
_QDRANT_CLIENT = None


def _get_embedding_model():
    """Lazily load embedding model on first use."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _EMBEDDING_MODEL = SentenceTransformer(settings.embedding_model)
    return _EMBEDDING_MODEL


def _get_qdrant_client():
    """Lazily initialize Qdrant client on first use."""
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        logger.info(f"Initializing Qdrant client: {settings.qdrant_url}")
        _QDRANT_CLIENT = QdrantVectorDB(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
        )
    return _QDRANT_CLIENT


@dataclass
class RetrievedChunk:
    """Chunk returned from Qdrant search."""

    chunk_id: str
    text: str
    similarity_score: float
    dept: str
    visibility: str
    trust_score: float
    source_file: str


def embed_text(text: str) -> List[float]:
    """
    Embed text using sentence-transformers all-MiniLM-L6-v2 model.

    Args:
        text: Text to embed

    Returns:
        384-dimensional embedding vector
    """
    model = _get_embedding_model()
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()


async def retrieve_chunks(
    query_text: str,
    role: str,
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """
    Retrieve chunks from Qdrant with RBAC filtering (US-201, US-202, US-203).

    **Critical Security:** RBAC filter is injected BEFORE the vector search query,
    ensuring unauthorized chunks are excluded from the search space entirely,
    not just filtered after retrieval.

    Steps:
      1. Embed query text
      2. Get RBAC filter for user role
      3. Search Qdrant with filter applied (pre-retrieval)
      4. Return top_k authorized chunks

    Args:
        query_text: User's natural language query
        role: User's role (admin, finance, hr, standard)
        top_k: Number of chunks to return (default: 5)

    Returns:
        List of RetrievedChunk objects authorized for the role

    Raises:
        ValueError: If role is not recognized
    """
    try:
        # Step 1: Embed the query
        query_embedding = embed_text(query_text)
        logger.debug(f"Query embedded. Embedding shape: {len(query_embedding)}")

        # Step 2: Get RBAC filter for role (raises ValueError if role invalid)
        rbac_filter = get_filter_for_role(role)
        logger.info(f"Retrieved RBAC filter for role '{role}'")

        # Step 3: Search Qdrant with filter (pre-retrieval, security-critical)
        qdrant = _get_qdrant_client()
        search_result = qdrant.search(
            query_vector=query_embedding,
            query_filter=rbac_filter,  # Filter applied BEFORE search
            limit=top_k,
        )

        logger.info(f"Qdrant returned {len(search_result)} results for role '{role}'")

        # Step 4: Convert Qdrant points to RetrievedChunk objects
        retrieved_chunks = []
        for point in search_result:
            payload = point.payload
            chunk = RetrievedChunk(
                chunk_id=payload.get("chunk_id", "unknown"),
                text=payload.get("text", ""),
                similarity_score=point.score,
                dept=payload.get("dept", "unknown"),
                visibility=payload.get("visibility", "unknown"),
                trust_score=payload.get("trust_score", 0.0),
                source_file=payload.get("source_file", "unknown"),
            )
            retrieved_chunks.append(chunk)

        logger.info(f"Returning {len(retrieved_chunks)} authorized chunks to role '{role}'")
        return retrieved_chunks

    except ValueError as e:
        logger.error(f"Invalid role or filter error: {e}")
        raise
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise
