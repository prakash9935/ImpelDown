"""
Ingestion Pipeline Orchestrator (Epic 1)

Coordinates: parse → sanitize → tag → embed → store

Pipeline Steps:
  1. parse_pdf(file_path) → List[Chunk]
  2. scrub_hidden_text(chunk.text) → clean_text
  3. flag_adversarial_language(clean_text) → is_adversarial
  4. tag_chunk(...) → TaggedChunk with trust_score
  5. embed_text(text) → embedding (TODO: Sprint 2)
  6. store_in_qdrant(embedding, metadata) → void (TODO: Sprint 2)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.secrag.config import settings
from src.secrag.retrieval.qdrant_client import QdrantVectorDB
from src.secrag.retrieval.retriever import embed_text

from . import parser, sanitizer, tagger

logger = logging.getLogger(__name__)


async def ingest_document(
    file_path: str,
    dept: str,
    visibility: str,
    base_tier: int = 1,
    author_role: Optional[str] = None,
) -> Dict[str, any]:
    """
    End-to-end document ingestion pipeline (Epic 1).

    Orchestrates:
      1. Parse PDF into chunks
      2. Scrub hidden text from each chunk
      3. Flag adversarial language
      4. Tag chunks with RBAC metadata
      5. Compute embeddings (sentence-transformers)
      6. Store in Qdrant with metadata

    Args:
        file_path: Path to PDF file
        dept: Department (finance, hr, corp, public)
        visibility: Visibility level (public, internal, restricted)
        base_tier: Trust tier (0-3)
        author_role: Document author's role

    Returns:
        {
            "status": "success" | "partial" | "error",
            "file_name": str,
            "chunks_ingested": int,
            "chunks_embedded": int,
            "chunks_quarantined": int,
            "errors": List[str],
            "timestamp": datetime,
        }
    """
    errors: List[str] = []
    tagged_chunks: List[tagger.TaggedChunk] = []
    chunks_quarantined = 0

    try:
        # Initialize Qdrant client for Steps 5-6 (embedding + storage)
        qdrant = QdrantVectorDB(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
        )

        # Step 1: Parse PDF
        logger.info(f"Step 1/6: Parsing PDF {file_path}")
        chunks = parser.parse_pdf(file_path)
        logger.info(f"  → Extracted {len(chunks)} chunks")
        chunks_embedded = 0

        # Step 2-4: Sanitize, flag, and tag each chunk
        for chunk in chunks:
            try:
                # Step 2: Scrub hidden text
                clean_text = sanitizer.scrub_hidden_text(chunk.text)

                # Step 3: Flag adversarial language
                is_adversarial, reason = sanitizer.flag_adversarial_language(clean_text)
                if is_adversarial:
                    logger.warning(
                        f"Adversarial content detected in chunk {chunk.chunk_index}: {reason}"
                    )

                # Step 4: Tag with RBAC metadata
                tagged_chunk = tagger.tag_chunk(
                    text=clean_text,
                    source_file=chunk.source_file,
                    dept=dept,
                    visibility=visibility,
                    base_tier=base_tier,
                    author_role=author_role,
                )

                # Step 5: Embed the cleaned text
                try:
                    embedding = embed_text(clean_text)
                    logger.debug(f"Chunk {tagged_chunk.chunk_id} embedded (dim={len(embedding)})")
                except Exception as e:
                    error_msg = f"Failed to embed chunk {chunk.chunk_index}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    embedding = None

                # Step 6: Store chunk + embedding in Qdrant
                if embedding is not None:
                    try:
                        qdrant.upsert_chunk(
                            chunk_id=tagged_chunk.chunk_id,
                            embedding=embedding,
                            tagged_chunk=tagged_chunk,
                        )
                        chunks_embedded += 1
                        logger.debug(f"Chunk {tagged_chunk.chunk_id} stored in Qdrant")
                    except Exception as e:
                        error_msg = f"Failed to store chunk {chunk.chunk_index} in Qdrant: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)

                # Track quarantined chunks
                if tagged_chunk.quarantine:
                    chunks_quarantined += 1
                    logger.warning(
                        f"Chunk {tagged_chunk.chunk_id} quarantined (trust_score={tagged_chunk.trust_score:.2f} < 1.5)"  # noqa: E501
                    )

                tagged_chunks.append(tagged_chunk)

            except Exception as e:
                error_msg = f"Failed to process chunk {chunk.chunk_index}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Embedding and Qdrant storage complete (Steps 5-6)
        logger.info("Step 2/6: Sanitization complete")
        logger.info("Step 3/6: Flagging complete")
        logger.info("Step 4/6: Tagging complete")
        logger.info(f"Step 5/6: Embedding complete ({chunks_embedded} embeddings)")
        logger.info("Step 6/6: Qdrant storage complete")
        logger.info(
            f"  → {len(tagged_chunks)} chunks processed, {chunks_embedded} embedded+stored, {chunks_quarantined} quarantined"  # noqa: E501
        )

        return {
            "status": "success" if not errors else "partial",
            "file_name": chunk.source_file if chunks else "unknown",
            "chunks_ingested": len(tagged_chunks),
            "chunks_embedded": chunks_embedded,
            "chunks_quarantined": chunks_quarantined,
            "errors": errors,
            "timestamp": datetime.utcnow(),
            "tagged_chunks": tagged_chunks,  # Return for testing/debugging
        }

    except Exception as e:
        error_msg = f"Ingestion pipeline failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "file_name": file_path,
            "chunks_ingested": 0,
            "chunks_quarantined": 0,
            "errors": [error_msg],
            "timestamp": datetime.utcnow(),
        }
