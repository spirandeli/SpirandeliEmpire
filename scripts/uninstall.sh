#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Safe Uninstall Script
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}WARNING: You are about to uninstall SpirandeliEmpire OS.${NC}"
read -p "Type 'DELETE-EMPIRE' to confirm uninstallation: " CONFIRM

if [ "$CONFIRM" != "DELETE-EMPIRE" ]; then
    echo "Aborted."
    exit 0
fi

echo -e "${YELLOW}==> Generating final backup before teardown...${NC}"
./scripts/backup.sh || true

echo -e "${YELLOW}==> Stopping and removing containers and networks...${NC}"
docker compose down -v

echo -e "SpirandeliEmpire OS containers and volumes have been removed."
echo "Your backups remain safe in ${BACKUP_STORAGE_PATH:-/var/spirandeli/backups}."

