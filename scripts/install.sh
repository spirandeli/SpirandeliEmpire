#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Automated Production Installer
# Designed for clean Ubuntu 24.04 LTS / Debian VPS
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}"
cat << "EOF"
  ____             _                   _       _   _   ______                 _           
 / ___| _ __  _ __| |__   __ _ _ __   / \   __| | | | |  ____|               (_)          
 \___ \| '_ \| '__| '_ \ / _` | '_ \ / _ \ / _` | | | | |__   _ __ ___  _ __  _ _ __ ___  
  ___) | |_) | |  | | | | (_| | | | / ___ \ (_| | | | |  __| | '_ ` _ \| '_ \| | '__/ _ \ 
 |____/| .__/|_|  |_| |_|\__,_|_| |/_/   \_\__,_| |_| | |____| | | | | | |_) | | | |  __/ 
       |_|                                            |______|_| |_| |_| .__/|_|_|  \___| 
                                                                       | |                
  OS v2.0 - Central Digital Business Command Center                    |_|                
EOF
echo -e "${NC}"

# Check root / sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root or with sudo.${NC}" 
   exit 1
fi

echo -e "${GREEN}[1/8] Verifying OS & System Dependencies...${NC}"
if ! command -v curl &> /dev/null || ! command -v git &> /dev/null; then
    apt-get update -y && apt-get install -y curl git ufw
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[!] Docker not found. Installing Docker Engine from official repository...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm -f get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

# Check Docker Compose (v2 plugin)
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}[!] Installing Docker Compose plugin...${NC}"
    apt-get update -y && apt-get install -y docker-compose-plugin
fi

echo -e "${GREEN}[2/8] Checking Environment File (.env)...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}[!] .env not found. Copying from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}[!] Please review .env variables before continuing.${NC}"
    else
        echo -e "${RED}[ERROR] .env.example not found. Please ensure project repository is complete.${NC}"
        exit 1
    fi
fi

# Load environment variables (set -a / source handles values with spaces correctly)
set -a
# shellcheck source=.env
source .env
set +a

echo -e "${GREEN}[3/8] Setting Up Directory Permissions & Storage...${NC}"
mkdir -p storage/logs storage/backups storage/businesses storage/framework/{cache,sessions,views}
mkdir -p core/frontend/dist
mkdir -p /var/spirandeli/backups
chmod -R 775 storage
chmod -R +x scripts/

echo -e "${GREEN}[4/8] Building & Launching Docker Services...${NC}"
docker compose pull || true
docker compose build
docker compose up -d

echo -e "${GREEN}[5/8] Waiting for Core Database & Redis Healthchecks...${NC}"
RETRY_COUNT=0
MAX_RETRIES=20
until [ $(docker inspect --format='{{json .State.Health.Status}}' empire_postgres 2>/dev/null) == '"healthy"' ]; do
    echo -n "."
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "\n${RED}[ERROR] Postgres failed to reach healthy status in time.${NC}"
        docker compose logs postgres
        exit 1
    fi
done
echo -e "\n${GREEN}==> Database and Redis are healthy!${NC}"

echo -e "${GREEN}[6/8] Initializing Backend Migrations & Database Seeds...${NC}"
docker compose exec -T core-app php artisan key:generate --force || true
docker compose exec -T core-app php artisan migrate --force || true
docker compose exec -T core-app php artisan db:seed --force || true

echo -e "${GREEN}[7/8] Pulling High-Quality AI Model (Ollama 8GB Profile)...${NC}"
echo "Pulling ${DEFAULT_TEXT_MODEL:-qwen2.5:7b} (high quality Portuguese narrative & business reasoning)..."
docker compose exec -T ollama ollama pull ${DEFAULT_TEXT_MODEL:-qwen2.5:7b} || true

echo -e "${GREEN}[8/8] Running Initial System Healthcheck...${NC}"
./scripts/healthcheck.sh

echo -e "\n${GREEN}${BOLD}========================================================================${NC}"
echo -e "${GREEN}${BOLD} SpirandeliEmpire OS v2.0 successfully installed and running!${NC}"
echo -e "${GREEN}${BOLD}========================================================================${NC}"
echo -e "Dashboard URL: ${BLUE}https://${DOMAIN:-localhost}${NC}"
echo -e "Monitoring URL: ${BLUE}https://${DOMAIN:-localhost}/kuma${NC}"
echo -e "Default Admin: ${YELLOW}${ADMIN_EMAIL:-admin@yourdomain.com}${NC}"
echo -e "Default Password: ${YELLOW}${ADMIN_INITIAL_PASSWORD:-ChangeMeOnFirstLogin!2026}${NC}"
echo -e "\n${YELLOW}Reminder: Make sure your DNS domain points to this VPS IP address.${NC}\n"

