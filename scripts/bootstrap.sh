#!/usr/bin/env bash
# Bootstrap do ambiente DEV: prepara o ambiente Python FastAPI + Vue 3.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { cp .env.example .env; echo ">> .env criado"; }
[ -f backend-python/.env ] || { cp backend-python/.env.example backend-python/.env 2>/dev/null || touch backend-python/.env; echo ">> backend-python/.env verificado"; }

HOST_UID="$(id -u)"; HOST_GID="$(id -g)"
sed -i "s/^UID=.*/UID=${HOST_UID}/; s/^GID=.*/GID=${HOST_GID}/" .env

echo ">> Subindo serviços de dados (MySQL, Redis, Mailpit)..."
docker compose up -d db redis mailpit

echo ">> Aguardando MySQL inicializar..."
sleep 5

echo ">> Subindo backend Python FastAPI e frontend Vue..."
docker compose up -d --build

echo ">> Executando seed de dados no FastAPI..."
docker compose exec -T app-py python3 src/seed.py

echo "Pronto: http://localhost:${WEB_PORT:-8080} | Mailpit: http://localhost:${MAILPIT_UI_PORT:-8025}"
