"""
Qdrant Vector Database Client (Sprint 2, US-201)

Initializes connection to Qdrant and manages collection setup.

Implements:
  - QdrantClient wrapper class with connection management
  - ensure_collection_exists() - create if missing with COSINE distance metric
  - upsert_chunk() - store TaggedChunk with embedding vector
  - health_check() - verify Qdrant connectivity
"""

import logging
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.secrag.ingestion.tagger import TaggedChunk

logger = logging.getLogger(__name__)


class QdrantVectorDB:
    """Wrapper around Qdrant client for SecRAG (Sprint 2, US-201)."""

    def __init__(self, url: str, collection_name: str, vector_size: int = 384):
        """
        Initialize Qdrant connection and ensure collection exists.

        Args:
            url: Qdrant server URL (e.g., http://localhost:6333)
            collection_name: Name of collection to use
            vector_size: Embedding dimension (default: 384 for all-MiniLM-L6-v2)
        """
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(url)
        self.ensure_collection_exists()
        logger.info(f"Qdrant connection initialized. Collection: {collection_name}")

    def ensure_collection_exists(self) -> None:
        """
        Create collection if it doesn't exist with proper schema for RBAC filtering.

        Collection: `secrag_docs` with COSINE distance metric and payload fields
        for dept, visibility, trust_score, chunk_id, source_file.
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.debug(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise

    def upsert_chunk(
        self, chunk_id: str, embedding: List[float], tagged_chunk: TaggedChunk
    ) -> None:
        """
        Store a chunk with its embedding vector in Qdrant.

        Args:
            chunk_id: Unique chunk identifier
            embedding: 384-dim embedding vector
            tagged_chunk: TaggedChunk object with metadata
        """
        try:
            payload = {
                "text": tagged_chunk.text,
                "source_file": tagged_chunk.source_file,
                "dept": tagged_chunk.dept,
                "visibility": tagged_chunk.visibility,
                "trust_score": tagged_chunk.trust_score,
                "base_tier": tagged_chunk.base_tier,
                "quarantine": tagged_chunk.quarantine,
                "ingestion_timestamp": tagged_chunk.ingestion_timestamp.isoformat(),
            }

            # Convert chunk_id to integer for Qdrant (required for PointStruct)
            point_id = hash(chunk_id) & 0x7FFFFFFF  # Ensure positive 32-bit int

            point = PointStruct(id=point_id, vector=embedding, payload=payload)
            self.client.upsert(collection_name=self.collection_name, points=[point])
            logger.debug(f"Upserted chunk {chunk_id} to Qdrant")

        except Exception as e:
            logger.error(f"Failed to upsert chunk {chunk_id}: {e}")
            raise

    def search(self, query_vector: List[float], query_filter=None, limit: int = 5):
        """
        Search Qdrant collection with vector similarity and optional filter.

        Args:
            query_vector: Query embedding vector (384-dim)
            query_filter: Optional Qdrant filter for RBAC
            limit: Max results to return

        Returns:
            List of scored points from Qdrant
        """
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
            )
            logger.debug(f"Search returned {len(results.points)} results")
            return results.points
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def health_check(self) -> bool:
        """Check if Qdrant is reachable and responding."""
        try:
            self.client.get_collections()
            logger.debug("Qdrant health check passed")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
