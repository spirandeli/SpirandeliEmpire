#!/usr/bin/env bash
set -euo pipefail

# SpirandeliEmpire OS 3.2 — Zero-Downtime-Safe Production Deploy & Migration Script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

echo "[deploy] Building and starting containers..."
docker compose up -d --build

echo "[deploy] Running Alembic migrations inside backend container..."
docker compose exec -T backend alembic upgrade head

echo "[deploy] Refreshing nginx upstream DNS..."
docker compose restart nginx

echo "[deploy] Verifying /health endpoint..."
for i in $(seq 1 15); do
  if curl -fsS "http://localhost:${WEB_PORT:-8086}/health"; then
    echo ""
    echo "[deploy] Deployment verified healthy."
    exit 0
  fi
  sleep 2
done

echo "[deploy] Health check failed after timeout."
exit 1

