"""
Configuration management using Pydantic Settings.

Loads environment variables from .env and provides type-safe config access.
See .env.example for all required and optional settings.
"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # === Application ===
    app_name: str = "SecRAG"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # === API Server ===
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    cors_origins: Optional[str] = None  # Comma-separated list of allowed origins

    # === OIDC/JWT ===
    oidc_issuer_url: str
    oidc_client_id: str
    oidc_client_secret: str
    jwt_algorithm: str = "RS256"
    jwt_expiration_hours: int = 8

    # === Qdrant ===
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "secrag"
    qdrant_vector_size: int = 384

    # === Redis ===
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 86400
    redis_session_ttl_seconds: int = 28800

    # === LLM ===
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    # === Embeddings ===
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # === LangSmith ===
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "secrag-dev"

    # === Guardrails ===
    pii_redaction_enabled: bool = True

    # === Ingestion ===
    trust_score_min_threshold: float = 1.5

    # === Rate Limiting ===
    rate_limit_per_minute: int = 10
    rate_limit_tokens_per_day: int = 100000

    # === Department Quotas ===
    dept_finance_quota: int = 500000
    dept_hr_quota: int = 100000
    dept_standard_quota: int = 50000

    # === Logging ===
    structured_logging: bool = True
    log_to_stdout: bool = True

    # === Alerts ===
    slack_webhook_url: Optional[str] = None

    # === Testing ===
    testing: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


# Singleton instance
settings = Settings()
