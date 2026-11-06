#!/bin/sh
set -e

cd /var/www/html

# Garante diretórios graváveis do Laravel (se o skeleton já existir)
if [ -f artisan ]; then
    mkdir -p storage/framework/cache storage/framework/sessions storage/framework/views storage/logs bootstrap/cache
    chown -R www-data:www-data storage bootstrap/cache 2>/dev/null || true
    chmod -R ug+rwX storage bootstrap/cache 2>/dev/null || true

    if [ ! -f vendor/autoload.php ]; then
        echo "[app] vendor/ ausente - executando composer install..."
        su -s /bin/sh www-data -c "composer install --no-interaction --prefer-dist"
    fi
else
    echo "[app] Laravel ainda não instalado. Rode ./scripts/bootstrap.sh"
fi

exec "$@"
