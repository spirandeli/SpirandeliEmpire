#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Update Script
# ==============================================================================
set -euo pipefail

echo "==> [1/6] Running pre-update backup..."
./scripts/backup.sh

echo "==> [2/7] Pulling latest changes from Git..."
git pull origin main || git pull

if [ -f .env ]; then
    sed -i 's/qwen2.5:7b/qwen2.5:3b/g' .env || true
fi

echo "==> [3/7] Building Frontend (Vue 3 SPA) into core/frontend/dist..."
docker run --rm -v "$(pwd)/core/frontend:/app" -w /app node:20-alpine sh -c "npm install --no-audit --no-fund && npm run build" || true

echo "==> [4/7] Rebuilding and starting updated containers..."
docker compose build core-app core-worker jeffrey-worker jeffrey-telegram
docker compose up -d --force-recreate core-app core-worker jeffrey-worker jeffrey-telegram caddy

echo "==> [5/7] Installing/updating Composer dependencies & clearing caches..."
docker compose exec -T core-app composer install --no-dev --optimize-autoloader --no-interaction --ignore-platform-reqs || true
docker compose exec -T core-app php artisan config:clear || true
docker compose exec -T core-app php artisan route:clear || true

echo "==> [6/7] Running database migrations..."
docker compose exec -T core-app php artisan migrate --force

echo "==> [7/7] Ensuring local lightweight AI model is present in Ollama (and removing heavy 7b OOM model)..."
docker compose exec -T ollama ollama pull qwen2.5:3b || true
docker compose exec -T ollama ollama rm qwen2.5:7b 2>/dev/null || true

echo "==> Update completed successfully!"
./scripts/healthcheck.sh
