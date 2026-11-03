#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Update Script
# ==============================================================================
set -euo pipefail

echo "==> [1/4] Running pre-update backup..."
./scripts/backup.sh

echo "==> [2/4] Pulling latest changes from Git..."
git pull origin main || git pull

echo "==> [3/4] Rebuilding updated containers..."
docker compose build core-app core-worker jeffrey-worker
docker compose up -d

echo "==> [4/4] Running database migrations..."
docker compose exec -T core-app php artisan migrate --force

echo "==> Update completed successfully!"
./scripts/healthcheck.sh

