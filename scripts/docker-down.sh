#!/bin/bash
# Stop and remove SecRAG services with Docker Compose
# Usage: ./scripts/docker-down.sh [--keep-volumes]

set -e

KEEP_VOLUMES=false
if [[ "$1" == "--keep-volumes" ]]; then
  KEEP_VOLUMES=true
fi

echo "🛑 Stopping SecRAG services..."

if [ "$KEEP_VOLUMES" = true ]; then
  docker compose down
  echo "✅ Services stopped (volumes preserved)"
else
  docker compose down -v
  echo "✅ Services stopped and volumes removed"
fi
