"""
Ingest Endpoint (POST /api/v1/ingest)

Upload and ingest a PDF document.

Auth: OIDC JWT required (admin role only)
Rate Limit: 10 req/min per user (shared with query endpoint)
Security: Admin-only access, document validation, error handling

Orchestrates: validate → save → parse → sanitize → tag → embed → store
"""

import logging
import os
import tempfile
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from src.secrag.ingestion.pipeline import ingest_document as ingest_doc_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestResponse(BaseModel):
    """Ingestion response summary."""

    status: str  # success, partial, error
    file_name: str
    chunks_ingested: int
    chunks_quarantined: int
    errors: List[str] = []


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    dept: str = Form(...),
    visibility: str = Form("internal"),
    base_tier: int = Form(1),
    http_request: Request = None,
) -> IngestResponse:
    """
    Upload and ingest a PDF document into the vector database.

    Security: Admin-only endpoint (checked via request.state.role set by AuthMiddleware)

    Args:
        file: PDF file to upload
        dept: Department (finance, hr, corp, public)
        visibility: Visibility level (public, internal, restricted)
        base_tier: Trust tier (0-3, higher = more trustworthy)
        http_request: FastAPI request object (contains auth context)

    Returns:
        IngestResponse with ingestion summary

    Raises:
        HTTPException(401): Missing authentication
        HTTPException(403): Not admin role
        HTTPException(400): Invalid file or parameters
        HTTPException(500): Ingestion pipeline failure
    """
    # Check authentication and admin role
    role = getattr(http_request.state, "role", None)
    user_id = getattr(http_request.state, "user_id", "unknown")

    if not role:
        logger.warning(f"Ingest request without auth context from {user_id}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    if role != "admin":
        logger.warning(f"Ingest attempt by non-admin user {user_id} (role={role})")
        raise HTTPException(status_code=403, detail="Only admins can ingest documents")

    # Validate parameters
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File is required")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if dept not in ["finance", "hr", "corp", "public"]:
        raise HTTPException(status_code=400, detail="Invalid department")

    if visibility not in ["public", "internal", "restricted"]:
        raise HTTPException(status_code=400, detail="Invalid visibility")

    if not isinstance(base_tier, int) or base_tier < 0 or base_tier > 3:
        raise HTTPException(status_code=400, detail="base_tier must be 0-3")

    logger.info(
        f"Ingest started for {file.filename} (dept={dept}, visibility={visibility}, tier={base_tier}) by {user_id}"  # noqa: E501
    )

    temp_file_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        logger.debug(f"File saved to {temp_file_path} ({len(content)} bytes)")

        # Call ingestion pipeline
        result = await ingest_doc_pipeline(
            file_path=temp_file_path,
            dept=dept,
            visibility=visibility,
            base_tier=base_tier,
            author_role=role,  # Assume document author is the uploader
        )

        logger.info(
            f"Ingestion completed: {result['chunks_ingested']} chunks, "
            f"{result['chunks_quarantined']} quarantined, "
            f"{len(result.get('errors', []))} errors"
        )

        return IngestResponse(
            status=result["status"],
            file_name=result.get("file_name", file.filename),
            chunks_ingested=result.get("chunks_ingested", 0),
            chunks_quarantined=result.get("chunks_quarantined", 0),
            errors=result.get("errors", []),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Ingest pipeline failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Document ingestion failed")

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up temp file {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {e}")
