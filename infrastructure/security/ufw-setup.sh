#!/usr/bin/env bash
# ==============================================================================
# SpirandeliEmpire OS - Firewall Hardening Script (UFW)
# ==============================================================================
set -euo pipefail

echo "==> Configuring UFW firewall for SpirandeliEmpire OS..."

if ! command -v ufw &> /dev/null; then
    echo "Installing UFW..."
    apt-get update && apt-get install -y ufw
fi

# Reset to defaults
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow standard SSH (adjust port if using non-standard SSH port)
ufw allow 22/tcp comment 'SSH Management'

# Allow Web Traffic (Reverse Proxy Caddy)
ufw allow 80/tcp comment 'Caddy HTTP'
ufw allow 443/tcp comment 'Caddy HTTPS'

# Block direct access to internal services from outside
# (PostgreSQL 5432, Redis 6379, Ollama 11434, Uptime Kuma 3001 are kept internal to Docker)

echo "==> Enabling UFW..."
ufw --force enable

echo "==> UFW status:"
ufw status verbose
echo "==> Firewall configuration completed successfully."

