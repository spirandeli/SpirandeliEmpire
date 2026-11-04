#!/bin/sh
export COMPOSER_ALLOW_SUPERUSER=1

# Auto-provision composer vendor with lock to avoid race conditions
if [ ! -f /var/www/backend/vendor/autoload.php ]; then
    LOCKFILE="/var/www/backend/.vendor_installing.lock"
    if [ -f "$LOCKFILE" ]; then
        echo "==> [Entrypoint] Another container is preparing vendor. Waiting..."
        while [ -f "$LOCKFILE" ]; do
            sleep 1
        done
    else
        touch "$LOCKFILE"
        echo "==> [Entrypoint] vendor/autoload.php not found. Provisioning..."
        if [ -d /var/www/vendor-base/vendor ]; then
            echo "==> [Entrypoint] Copying pre-built vendor from image cache..."
            cp -a /var/www/vendor-base/vendor /var/www/backend/
        else
            echo "==> [Entrypoint] Running composer install..."
            cd /var/www/backend
            composer install --no-dev --no-scripts --no-interaction --ignore-platform-reqs || true
            composer dump-autoload --optimize --no-scripts || true
        fi
        rm -f "$LOCKFILE"
    fi
fi

# Ensure essential runtime directories and permissions
mkdir -p /var/www/backend/storage/framework/cache/data
mkdir -p /var/www/backend/storage/framework/sessions
mkdir -p /var/www/backend/storage/framework/views
mkdir -p /var/www/backend/storage/logs
mkdir -p /var/spirandeli/businesses
chmod -R 777 /var/www/backend/storage /var/spirandeli/businesses 2>/dev/null || true

exec "$@"
