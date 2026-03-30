FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal - PDF parsing delegated to docling-serve)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY .env.example .env

# Install Python dependencies
RUN uv pip install -e . --system

# Copy source code
COPY src/ src/
COPY config/ config/
COPY tests/ tests/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run FastAPI app
CMD ["uvicorn", "src.secrag.main:app", "--host", "0.0.0.0", "--port", "8000"]
