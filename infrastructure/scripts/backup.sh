#!/usr/bin/env bash
set -euo pipefail

# SpirandeliEmpire OS 3.2 — Backup Script (PostgreSQL + Storage Artifacts & Checkpoints)
# Does NOT store plaintext .env secrets inside backup archives.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${1:-${ROOT_DIR}/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
WORK_DIR="$(mktemp -d)"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-spirandeli-postgres}"
POSTGRES_USER="${POSTGRES_USER:-spirandeli}"
POSTGRES_DB="${POSTGRES_DB:-spirandeliempire}"

mkdir -p "${BACKUP_DIR}"
trap 'rm -rf "${WORK_DIR}"' EXIT

echo "[backup] Dumping PostgreSQL database '${POSTGRES_DB}'..."
docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -Fc "${POSTGRES_DB}" > "${WORK_DIR}/postgres.dump"

echo "[backup] Archiving storage (artifacts + checkpoints)..."
tar -czf "${WORK_DIR}/storage.tar.gz" -C "${ROOT_DIR}" storage

OUT_ARCHIVE="${BACKUP_DIR}/spirandeli_backup_${TIMESTAMP}.tar.gz"
tar -czf "${OUT_ARCHIVE}" -C "${WORK_DIR}" postgres.dump storage.tar.gz
chmod 600 "${OUT_ARCHIVE}"

echo "[backup] Backup created successfully: ${OUT_ARCHIVE}"

