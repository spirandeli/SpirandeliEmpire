#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Automated Backup Script
# ==============================================================================
set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_STORAGE_PATH:-/var/spirandeli/backups}"
BACKUP_FILE="${BACKUP_DIR}/empire_backup_${TIMESTAMP}.tar.gz"
TEMP_DIR="/tmp/empire_backup_${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"
mkdir -p "${TEMP_DIR}"

echo "==> [1/4] Dumping PostgreSQL Database..."
docker compose exec -T postgres pg_dump -U empire_admin spirandeli_empire > "${TEMP_DIR}/database.sql"

echo "==> [2/4] Archiving configuration and business storage..."
cp -r storage/businesses "${TEMP_DIR}/businesses" 2>/dev/null || true
cp .env "${TEMP_DIR}/env.backup" 2>/dev/null || true

echo "==> [3/4] Creating compressed archive..."
tar -czf "${BACKUP_FILE}" -C "${TEMP_DIR}" .
rm -rf "${TEMP_DIR}"

# Compute SHA256 checksum
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"

echo "==> [4/4] Applying retention policy (cleaning backups older than 14 days)..."
find "${BACKUP_DIR}" -name "empire_backup_*.tar.gz*" -mtime +14 -delete

echo "==> Backup completed successfully: ${BACKUP_FILE}"
ls -lh "${BACKUP_FILE}"

