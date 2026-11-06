#!/bin/sh
set -e

cd /var/www/html

# O worker só sobe quando o Laravel estiver instalado, com APP_KEY e migrations aplicadas.
echo "[worker] Aguardando Laravel (vendor + APP_KEY)..."
until [ -f vendor/autoload.php ] && [ -f artisan ] && [ -n "${APP_KEY}" ]; do
    sleep 3
done

echo "[worker] Aguardando banco e tabela de migrations..."
until php -r '
try {
    $pdo = new PDO(
        sprintf("mysql:host=%s;port=%s;dbname=%s", getenv("DB_HOST"), getenv("DB_PORT") ?: "3306", getenv("DB_DATABASE")),
        getenv("DB_USERNAME"), getenv("DB_PASSWORD")
    );
    $pdo->query("SELECT 1 FROM migrations LIMIT 1");
    exit(0);
} catch (Throwable $e) { exit(1); }
' >/dev/null 2>&1; do
    sleep 3
done

mkdir -p storage/logs storage/framework/cache storage/framework/views bootstrap/cache
chown -R www-data:www-data storage bootstrap/cache 2>/dev/null || true

echo "[worker] Iniciando Supervisor."
exec "$@"
