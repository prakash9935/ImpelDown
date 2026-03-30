#!/bin/bash
# Start SecRAG services with Docker Compose
# Usage: ./scripts/docker-up.sh [--no-wait]

set -e

NO_WAIT=false
if [[ "$1" == "--no-wait" ]]; then
  NO_WAIT=true
fi

# SECURITY H-02/H-03: Generate strong random passwords if not set
if [ -z "$KEYCLOAK_ADMIN" ]; then
  export KEYCLOAK_ADMIN="admin"
fi

if [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
  export KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 24)
  echo "🔐 Generated Keycloak admin password: $KEYCLOAK_ADMIN_PASSWORD"
fi

if [ -z "$REDIS_PASSWORD" ]; then
  export REDIS_PASSWORD=$(openssl rand -base64 24)
  echo "🔐 Generated Redis password: $REDIS_PASSWORD"
fi

# SECURITY L-02: Safe env loading using source instead of export $(cat | xargs)
if [ -f .env.docker ]; then
  set -a
  source .env.docker
  set +a
  echo "Loaded .env.docker"
else
  echo "❌ .env.docker not found. Copy .env.example to .env.docker and configure it."
  exit 1
fi

# Pre-flight: verify .env.docker and .env don't have stale vars
echo "🔍 Pre-flight config check..."
KNOWN_STALE="LLM_PROVIDER GUARDRAIL_MODEL DOCLING_PARSING_ENGINE AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_S3_BUCKET ALERT_EMAIL_RECIPIENTS"
STALE_FOUND=false
for var in $KNOWN_STALE; do
  for envfile in .env .env.docker; do
    if [ -f "$envfile" ] && grep -q "^${var}=" "$envfile" 2>/dev/null; then
      echo "  ⚠️  Stale variable ${var} found in ${envfile} — remove it"
      STALE_FOUND=true
    fi
  done
done
if [ "$STALE_FOUND" = true ]; then
  echo "❌ Remove stale variables before starting. See config.py Settings class for valid fields."
  exit 1
fi
echo "  ✅ Config check passed"

echo "🚀 Starting SecRAG services..."
docker compose up -d

if [ "$NO_WAIT" = false ]; then
  echo "⏳ Waiting for services to be healthy..."

  # Wait for Qdrant
  echo "  Waiting for Qdrant..."
  until curl -f http://localhost:6333/readyz > /dev/null 2>&1; do
    sleep 2
  done
  echo "  ✅ Qdrant healthy"

  # Wait for Redis (simple port check)
  echo "  Waiting for Redis..."
  until (echo > /dev/tcp/localhost/6379) 2>/dev/null; do
    sleep 2
  done
  echo "  ✅ Redis healthy"

  # Wait for Keycloak (takes longer to boot)
  echo "  Waiting for Keycloak..."
  KEYCLOAK_TIMEOUT=0
  until [ $KEYCLOAK_TIMEOUT -gt 120 ] || (echo > /dev/tcp/localhost/8080) 2>/dev/null; do
    sleep 2
    KEYCLOAK_TIMEOUT=$((KEYCLOAK_TIMEOUT + 2))
  done
  if [ $KEYCLOAK_TIMEOUT -gt 120 ]; then
    echo "  ⚠️  Keycloak timeout (still starting), continuing..."
  else
    echo "  ✅ Keycloak healthy"
  fi

  # Wait for App (just check port is open)
  echo "  Waiting for App..."
  until (echo > /dev/tcp/localhost/8000) 2>/dev/null; do
    sleep 2
  done
  echo "  ✅ App healthy"

  echo ""
  echo "✨ All services are running!"
  echo ""
  echo "📍 Service URLs:"
  echo "  App:       http://localhost:8000"
  echo "  Qdrant:    http://localhost:6333"
  echo "  Redis:     localhost:6379"
  echo "  Keycloak:  http://localhost:8080"
  echo ""
else
  echo "✨ Services started (use docker compose logs -f to monitor)"
fi
