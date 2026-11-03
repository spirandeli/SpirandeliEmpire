#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Restore Script
# ==============================================================================
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 /path/to/empire_backup_YYYYMMDD_HHMMSS.tar.gz"
    exit 1
fi

ARCHIVE_PATH="$1"

if [ ! -f "${ARCHIVE_PATH}" ]; then
    echo "Error: Archive file not found: ${ARCHIVE_PATH}"
    exit 1
fi

# Verify SHA256 if hash file exists
if [ -f "${ARCHIVE_PATH}.sha256" ]; then
    echo "==> Verifying SHA256 integrity..."
    sha256sum -c "${ARCHIVE_PATH}.sha256"
fi

TEMP_DIR="/tmp/empire_restore_$(date +%s)"
mkdir -p "${TEMP_DIR}"
echo "==> Extracting archive..."
tar -xzf "${ARCHIVE_PATH}" -C "${TEMP_DIR}"

read -p "WARNING: Restoring will overwrite the current database. Proceed? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Restoration aborted."
    rm -rf "${TEMP_DIR}"
    exit 0
fi

echo "==> Restoring database..."
docker compose exec -T postgres psql -U empire_admin -d spirandeli_empire < "${TEMP_DIR}/database.sql"

if [ -d "${TEMP_DIR}/businesses" ]; then
    echo "==> Restoring businesses storage..."
    cp -r "${TEMP_DIR}/businesses"/* storage/businesses/ 2>/dev/null || true
fi

rm -rf "${TEMP_DIR}"
echo "==> Restoration completed successfully!"

