#!/usr/bin/env bash
# Bootstrap do ambiente DEV: instala o skeleton Laravel (se necessário), Sanctum, gera APP_KEY e migra.
# Idempotente: arquivos já existentes em backend/ (migrations, models, .env.example) NUNCA são sobrescritos.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { cp .env.example .env; echo ">> .env criado (ajuste as senhas!)"; }
[ -f backend/.env ] || { cp backend/.env.example backend/.env; echo ">> backend/.env criado"; }

# UID é variável readonly no bash: gravamos UID/GID do host direto no .env lido pelo compose.
HOST_UID="$(id -u)"; HOST_GID="$(id -g)"
sed -i "s/^UID=.*/UID=${HOST_UID}/; s/^GID=.*/GID=${HOST_GID}/" .env

echo ">> Build das imagens..."
docker compose build app worker

echo ">> Instalando skeleton Laravel 12 (preservando nossos arquivos)..."
docker compose run --rm --no-deps -u www-data app bash -lc '
  set -e
  if [ ! -f artisan ]; then
    composer create-project laravel/laravel:^12.0 /tmp/skel --prefer-dist --no-interaction
    rsync -a --ignore-existing /tmp/skel/ /var/www/html/
    rm -rf /tmp/skel
  fi
  [ -d vendor ] || composer install --no-interaction --prefer-dist
  composer show laravel/sanctum >/dev/null 2>&1 || composer require laravel/sanctum --no-interaction
  grep -q "^APP_KEY=base64" .env || php artisan key:generate --force
'

echo ">> Subindo serviços de dados..."
docker compose up -d db redis mailpit

echo ">> Publicando Sanctum e rodando migrations..."
docker compose run --rm -u www-data app bash -lc '
  set -e
  php artisan vendor:publish --provider="Laravel\Sanctum\SanctumServiceProvider" --tag=sanctum-migrations --no-interaction || true
  php artisan migrate --force
'

echo ">> Subindo stack completa..."
docker compose up -d
echo "Pronto: http://localhost:${WEB_PORT:-8080} | Mailpit: http://localhost:${MAILPIT_UI_PORT:-8025}"
