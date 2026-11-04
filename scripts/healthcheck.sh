#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Healthcheck Script
# ==============================================================================
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================"
echo " SpirandeliEmpire OS - System Health Diagnostics"
echo "======================================================"

# Check containers status
echo -e "\n[1] Containers Status:"
docker compose ps

# Check Postgres
echo -e "\n[2] Database Check:"
if docker compose exec -T postgres pg_isready -U empire_admin &>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is healthy and accepting connections.${NC}"
else
    echo -e "${RED}✗ PostgreSQL is unreachable!${NC}"
fi

# Check Redis
echo -e "\n[3] Redis Cache Check:"
if docker compose exec -T redis redis-cli ping &>/dev/null; then
    echo -e "${GREEN}✓ Redis is active.${NC}"
else
    echo -e "${RED}✗ Redis is unreachable!${NC}"
fi

# Check Ollama AI
echo -e "\n[4] Local AI (Ollama) Check:"
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo -e "${GREEN}✓ Ollama AI inference server is active.${NC}"
else
    echo -e "${YELLOW}! Ollama is internal or starting up.${NC}"
fi

# Check Disk Space
echo -e "\n[5] Disk Space:"
df -h / | awk 'NR==1 || NR==2 {print $0}'

# Check Memory
echo -e "\n[6] Memory Usage:"
free -h

echo -e "\n======================================================"
echo " Diagnostics Completed."
echo "======================================================"

