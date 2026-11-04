#!/bin/sh
set -e

# Auto-install composer dependencies if vendor does not exist in mounted volume
if [ ! -f /var/www/backend/vendor/autoload.php ]; then
    echo "==> [Entrypoint] vendor/autoload.php not found. Running composer install..."
    cd /var/www/backend
    composer install --no-dev --optimize-autoloader --no-interaction
fi

exec "$@"

