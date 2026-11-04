#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Update Script
# ==============================================================================
set -euo pipefail

echo "==> [1/5] Running pre-update backup..."
./scripts/backup.sh

echo "==> [2/5] Pulling latest changes from Git..."
git pull origin main || git pull

echo "==> [3/5] Rebuilding and starting updated containers..."
docker compose build core-app core-worker jeffrey-worker
docker compose up -d

echo "==> [4/5] Installing/updating Composer dependencies..."
docker compose exec -T core-app composer install --no-dev --optimize-autoloader --no-interaction

echo "==> [5/5] Running database migrations..."
docker compose exec -T core-app php artisan migrate --force

echo "==> Update completed successfully!"
./scripts/healthcheck.sh
