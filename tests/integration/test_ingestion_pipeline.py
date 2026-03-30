"""
Integration tests for ingestion pipeline (Sprint 1+).

Tests:
  - Admin-only access to ingest endpoint
  - File type validation
  - Department validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO


@pytest.mark.asyncio
async def test_ingest_pdf_admin_only(test_client, mock_qdrant_client, mock_redis_client, admin_claims, finance_claims):
    """Test PDF ingest requires admin role."""
    # Create a mock PDF file
    pdf_content = b"%PDF-1.4\n%fake PDF content"

    with patch("src.secrag.gateway.auth.validate_jwt") as mock_jwt, \
         patch("src.secrag.ingestion.pipeline.ingest_document") as mock_ingest:

        mock_ingest.return_value = {
            "file_name": "test.pdf",
            "chunks_ingested": 10,
            "chunks_quarantined": 0,
            "errors": []
        }

        # Test: Admin can ingest
        mock_jwt.return_value = admin_claims
        response = await test_client.post(
            "/api/v1/ingest",
            headers={"Authorization": "Bearer admin-token"},
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            data={"dept": "finance", "visibility": "internal", "base_tier": "1"}
        )
        assert response.status_code == 200, f"Admin ingest failed: {response.text}"

        # Test: Non-admin (Finance user) cannot ingest
        mock_jwt.return_value = finance_claims
        response = await test_client.post(
            "/api/v1/ingest",
            headers={"Authorization": "Bearer finance-token"},
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            data={"dept": "finance", "visibility": "internal", "base_tier": "1"}
        )
        assert response.status_code == 403, "Non-admin should not be able to ingest"


@pytest.mark.asyncio
async def test_ingest_non_pdf_rejected(test_client, admin_claims):
    """Test non-PDF file is rejected."""
    # Create a non-PDF file (TXT)
    txt_content = b"This is a text file, not a PDF"

    with patch("src.secrag.gateway.auth.validate_jwt") as mock_jwt:
        mock_jwt.return_value = admin_claims

        response = await test_client.post(
            "/api/v1/ingest",
            headers={"Authorization": "Bearer admin-token"},
            files={"file": ("test.txt", txt_content, "text/plain")},
            data={"dept": "finance", "visibility": "internal", "base_tier": "1"}
        )

        assert response.status_code == 400, "Non-PDF file should be rejected"
        data = response.json()
        assert "pdf" in data.get("detail", "").lower() or "file type" in data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_ingest_invalid_dept_rejected(test_client, admin_claims):
    """Test invalid department is rejected."""
    pdf_content = b"%PDF-1.4\n%fake PDF content"

    with patch("src.secrag.gateway.auth.validate_jwt") as mock_jwt:
        mock_jwt.return_value = admin_claims

        response = await test_client.post(
            "/api/v1/ingest",
            headers={"Authorization": "Bearer admin-token"},
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            data={"dept": "invalid_dept", "visibility": "internal", "base_tier": "1"}
        )

        assert response.status_code == 400, "Invalid department should be rejected"
        data = response.json()
        assert "department" in data.get("detail", "").lower() or "dept" in data.get("detail", "").lower()
