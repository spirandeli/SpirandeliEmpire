#!/usr/bin/env bash
set -euo pipefail

# SpirandeliEmpire OS 3.2 — Restore Script (PostgreSQL + Storage)
# Usage: ./restore.sh <backup_archive.tar.gz> [target_db_name] [target_storage_dir]

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_archive.tar.gz> [target_db_name] [target_storage_dir]"
  exit 1
fi

ARCHIVE_PATH="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DB="${2:-${POSTGRES_DB:-spirandeliempire}}"
TARGET_STORAGE_PARENT="${3:-${ROOT_DIR}}"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-spirandeli-postgres}"
POSTGRES_USER="${POSTGRES_USER:-spirandeli}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

if [ ! -f "${ARCHIVE_PATH}" ]; then
  echo "[restore] Error: archive not found: ${ARCHIVE_PATH}"
  exit 1
fi

tar -xzf "${ARCHIVE_PATH}" -C "${WORK_DIR}"

echo "[restore] Ensuring target database '${TARGET_DB}' exists..."
docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | grep -q 1 || \
  docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"

echo "[restore] Restoring PostgreSQL dump into '${TARGET_DB}'..."
cat "${WORK_DIR}/postgres.dump" | docker exec -i "${POSTGRES_CONTAINER}" pg_restore -U "${POSTGRES_USER}" -d "${TARGET_DB}" --clean --if-exists --no-owner

echo "[restore] Extracting storage into '${TARGET_STORAGE_PARENT}'..."
mkdir -p "${TARGET_STORAGE_PARENT}"
tar -xzf "${WORK_DIR}/storage.tar.gz" -C "${TARGET_STORAGE_PARENT}"

echo "[restore] Restore completed cleanly into DB '${TARGET_DB}' and '${TARGET_STORAGE_PARENT}/storage'."

