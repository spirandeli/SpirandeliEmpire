#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Update Script
# ==============================================================================
set -euo pipefail

echo "==> [1/6] Running pre-update backup..."
./scripts/backup.sh

echo "==> [2/6] Pulling latest changes from Git..."
git pull origin main || git pull

echo "==> [3/6] Rebuilding and starting updated containers..."
docker compose build core-app core-worker jeffrey-worker jeffrey-telegram
docker compose up -d

echo "==> [4/6] Installing/updating Composer dependencies..."
docker compose exec -T core-app composer install --no-dev --optimize-autoloader --no-interaction --ignore-platform-reqs || true

echo "==> [5/6] Running database migrations..."
docker compose exec -T core-app php artisan migrate --force

echo "==> [6/6] Ensuring local lightweight AI model is present in Ollama..."
docker compose exec -T ollama ollama pull qwen2.5:3b || true

echo "==> Update completed successfully!"
./scripts/healthcheck.sh
