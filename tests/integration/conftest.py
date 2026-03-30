"""
Pytest fixtures for integration tests.

Provides:
  - test_client: AsyncClient for FastAPI app
  - mock_qdrant: AsyncMock for Qdrant operations
  - mock_redis: AsyncMock for Redis operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from datetime import datetime
import os

# Set testing mode before importing app
os.environ["TESTING"] = "True"

from src.secrag.main import app
from src.secrag.retrieval.qdrant_client import QdrantVectorDB
from src.secrag.retrieval.rbac_filter import RBACFilter


@pytest.fixture
async def test_client():
    """AsyncClient for testing the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_qdrant():
    """AsyncMock for Qdrant operations."""
    mock = AsyncMock()

    # Mock health check
    mock.health_check = AsyncMock(return_value=True)

    # Mock search with RBAC filter
    mock.search = AsyncMock(
        return_value=[
            MagicMock(
                id="chunk_1",
                score=0.95,
                payload={
                    "text": "Sample finance data",
                    "dept": "finance",
                    "visibility": "internal",
                    "trust_score": 1.5,
                    "source_file": "doc1.pdf",
                    "quarantine": False,
                }
            )
        ]
    )

    # Mock upload
    mock.upload = AsyncMock(return_value={"status": "ok"})

    return mock


@pytest.fixture
def mock_redis():
    """AsyncMock for Redis operations."""
    mock = AsyncMock()

    # Mock ping
    mock.ping = AsyncMock(return_value=True)

    # Mock rate limit operations
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)

    # Mock quota operations
    mock.incrby = AsyncMock(return_value=100)
    mock.expireat = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def mock_qdrant_client(monkeypatch, mock_qdrant):
    """Patch QdrantVectorDB to use mock."""
    monkeypatch.setattr(
        "src.secrag.retrieval.qdrant_client.QdrantVectorDB",
        MagicMock(return_value=mock_qdrant)
    )
    return mock_qdrant


@pytest.fixture
def mock_redis_client(monkeypatch, mock_redis):
    """Patch Redis client to use mock."""
    monkeypatch.setattr(
        "src.secrag.gateway.rate_limiter.redis_client",
        mock_redis
    )
    return mock_redis


@pytest.fixture
def rbac_filter():
    """RBACFilter instance for testing."""
    return RBACFilter()


@pytest.fixture
def test_jwt_token():
    """JWT token for testing (TESTING=True disables signature verification)."""
    return "test-token-that-decodes-to-valid-claims"


@pytest.fixture
def admin_claims():
    """Admin JWT claims."""
    return {
        "sub": "admin-user-123",
        "realm_access": {"roles": ["admin"]},
        "exp": int(datetime.utcnow().timestamp()) + 3600,
        "iss": "http://localhost:8080/realms/secrag",
        "aud": "secrag-client"
    }


@pytest.fixture
def finance_claims():
    """Finance user JWT claims."""
    return {
        "sub": "finance-user-456",
        "realm_access": {"roles": ["finance"]},
        "exp": int(datetime.utcnow().timestamp()) + 3600,
        "iss": "http://localhost:8080/realms/secrag",
        "aud": "secrag-client"
    }


@pytest.fixture
def hr_claims():
    """HR user JWT claims."""
    return {
        "sub": "hr-user-789",
        "realm_access": {"roles": ["hr"]},
        "exp": int(datetime.utcnow().timestamp()) + 3600,
        "iss": "http://localhost:8080/realms/secrag",
        "aud": "secrag-client"
    }


@pytest.fixture
def standard_claims():
    """Standard user JWT claims."""
    return {
        "sub": "standard-user-000",
        "realm_access": {"roles": ["standard"]},
        "exp": int(datetime.utcnow().timestamp()) + 3600,
        "iss": "http://localhost:8080/realms/secrag",
        "aud": "secrag-client"
    }


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before each test."""
    original_testing = os.environ.get("TESTING")
    os.environ["TESTING"] = "True"
    yield
    if original_testing is not None:
        os.environ["TESTING"] = original_testing
    else:
        os.environ.pop("TESTING", None)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "load: load tests")
    config.addinivalue_line("markers", "asyncio: async tests")
