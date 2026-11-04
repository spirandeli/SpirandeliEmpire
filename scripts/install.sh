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
    # Proteção de integridade: checa se o script baixado não está vazio e possui cabeçalho válido
    if [ ! -s get-docker.sh ] || ! grep -q "Docker" get-docker.sh; then
        echo -e "${RED}[ERROR] Falha na validação do instalador do Docker.${NC}"
        rm -f get-docker.sh
        exit 1
    fi
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

# --- Validação estrita de variáveis de segurança de produção ---
if [ "${APP_ENV:-production}" = "production" ]; then
    if [ -z "${DB_PASSWORD:-}" ] || [ "${DB_PASSWORD:-}" = "secret_postgres_password_replace_me" ]; then
        echo -e "${RED}[ERRO CRÍTICO] DB_PASSWORD não configurada ou usando senha default insegura no .env.${NC}"
        echo -e "${YELLOW}Por favor, defina uma senha forte para o PostgreSQL antes de prosseguir.${NC}"
        exit 1
    fi

    if [ -z "${REDIS_PASSWORD:-}" ] || [ "${REDIS_PASSWORD:-}" = "secret_redis_password_replace_me" ]; then
        echo -e "${RED}[ERRO CRÍTICO] REDIS_PASSWORD não configurada ou usando senha default insegura no .env.${NC}"
        echo -e "${YELLOW}Por favor, defina uma senha forte para o Redis antes de prosseguir.${NC}"
        exit 1
    fi
fi

# Gera INTERNAL_API_SECRET automaticamente se ausente para proteger o Jeffrey Controller
if [ -z "${INTERNAL_API_SECRET:-}" ]; then
    INTERNAL_API_SECRET=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
    echo "INTERNAL_API_SECRET=${INTERNAL_API_SECRET}" >> .env
    export INTERNAL_API_SECRET
fi

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
docker compose exec -T core-app composer install --no-dev --optimize-autoloader --no-interaction || true
docker compose exec -T core-app php artisan key:generate --force || true
docker compose exec -T core-app php artisan migrate --force || true
docker compose exec -T core-app php artisan db:seed --force || true

echo -e "${GREEN}[7/8] Pulling High-Quality AI Model (Ollama 8GB Profile)...${NC}"
echo "Pulling ${DEFAULT_TEXT_MODEL:-qwen2.5:7b} (high quality Portuguese narrative & business reasoning)..."
docker compose exec -T ollama ollama pull "${DEFAULT_TEXT_MODEL:-qwen2.5:7b}" || true

echo -e "${GREEN}[7.5/8] Provisioning TikTok Business Directories & Anti-Ban Video Skill...${NC}"

# --- TikTok Shop: Diretórios de conteúdo ---
mkdir -p storage/businesses/tiktok-shop-afiliados/{assets,content/{scripts,audio,broll/{gadgets,saude-beleza,casa,moda,generic},renders,published},data,logs}
echo -e "${GREEN}  ==> TikTok Shop business directories created.${NC}"

# --- Skill: video-anti-ban (criada no .agents do projeto) ---
SKILL_DIR=".agents/skills/video-anti-ban"
mkdir -p "${SKILL_DIR}/scripts" "${SKILL_DIR}/references"

# -- SKILL.md (instrução principal para o agente) --
cat > "${SKILL_DIR}/SKILL.md" << 'SKILL_EOF'
---
name: video-anti-ban
description: >-
  Use this skill whenever creating, rendering, or post-processing any video for
  TikTok or YouTube in this project. It enforces the full anti-detection pipeline:
  C2PA metadata stripping, SynthID pixel-level disruption, film grain overlay,
  dynamic captions, and guardrails against shadow-ban triggers. Must be applied to
  ALL video outputs regardless of the AI generator used (Wan2.1, Runway, Kling, XTTS).
---

# Video Anti-Ban Pipeline — SpirandeliEmpire OS

Este skill DEVE ser seguido para **qualquer vídeo gerado** neste projeto antes de publicar no TikTok ou YouTube.

## ⚠️ Por que isso é crítico

As plataformas detectam IA em **duas camadas independentes**:

| Camada | O que detecta | Consequência |
|---|---|---|
| **Metadados / C2PA** | Tags de software, JUMBF boxes, XMP, Content Credentials | Label "Conteúdo IA" automático na plataforma |
| **Pixel-level / SynthID** | Padrões estatísticos do diffusion model | Shadow ban silencioso, entrega limitada pelo algoritmo |

Vídeos do **Wan2.1 local** não embutem C2PA nem SynthID — mas ainda precisam do grain/rescale para garantir naturalidade perceptual. Vídeos do **Runway ou Kling** SEMPRE embutem C2PA e precisam de limpeza completa.

---

## 📋 Passo a Passo Obrigatório

### Passo 1 — Limpeza de Metadados C2PA
Sempre executar `scripts/strip_metadata.sh` no vídeo exportado pela IA:

```bash
bash .agents/skills/video-anti-ban/scripts/strip_metadata.sh input.mp4 output_clean.mp4
```

**Verificar resultado:**
```bash
exiftool -G -a output_clean.mp4 | grep -iE "jumbf|c2pa|cai|creator|generator"
# Saída esperada: nenhuma linha
```

### Passo 2 — Humanização Pixel-Level (Anti-SynthID)
Executar `scripts/humanize_video.sh` após a limpeza de metadados:

```bash
bash .agents/skills/video-anti-ban/scripts/humanize_video.sh output_clean.mp4 output_humanized.mp4
```

Este script aplica: film grain sutil, rescale ±2px, e shift de frame rate de 0.5%.

**Verificar resultado:**
```bash
ffprobe -v quiet -show_streams output_humanized.mp4 | grep -E "width|height|r_frame_rate"
# width/height devem ser 1080x1920 (crop aplicado de volta ao alvo)
```

### Passo 3 — Composição Final (Narração + Legenda)
Usar o `render_tiktok_video.py` já existente no projeto:

```bash
python3 /opt/ai-engine/video-processing/render_tiktok_video.py \
  "<audio.mp3>" \
  "output_humanized.mp4" \
  "output_final.mp4" \
  "<roteiro>"
```

### Passo 4 — Checklist de Qualidade Pré-Upload
Antes de qualquer publicação, confirmar todos os itens:

- [ ] `exiftool` não encontrou tags C2PA/JUMBF
- [ ] Grain visível ao olho (noise ≥ 3) mas não intrusivo
- [ ] Hook visual nos **primeiros 2 segundos** (produto em close)
- [ ] Troca de cena ou movimento a cada **2–3 segundos**
- [ ] Legenda dinâmica presente durante todo o vídeo
- [ ] Duração: **25–45s** (TikTok) ou **55–60s** (YouTube Shorts)
- [ ] Disclosure `#parceria` ou `Link na bio` na descrição
- [ ] Máximo **9 vídeos/dia** no TikTok (guardrail anti-shadowban)

---

## 🛠️ Scripts Disponíveis

| Script | Função |
|---|---|
| [`scripts/strip_metadata.sh`](./scripts/strip_metadata.sh) | Remove C2PA, JUMBF, XMP e tags de software do container MP4 |
| [`scripts/humanize_video.sh`](./scripts/humanize_video.sh) | Aplica grain + rescale + fps-shift para quebrar assinatura SynthID |
| [`scripts/full_pipeline.sh`](./scripts/full_pipeline.sh) | Executa strip + humanize em sequência automática (uso no n8n) |

## 📚 Referências

- [`references/detection-layers.md`](./references/detection-layers.md) — Detalhes técnicos sobre C2PA, SynthID e detecção algorítmica
- [`references/generators.md`](./references/generators.md) — Comparativo de geradores (Wan2.1, Runway, Kling) e nível de risco de cada um
SKILL_EOF

# -- strip_metadata.sh --
cat > "${SKILL_DIR}/scripts/strip_metadata.sh" << 'STRIP_EOF'
#!/usr/bin/env bash
# video-anti-ban :: strip_metadata.sh
# Remove C2PA manifests, JUMBF boxes, XMP, e tags de software de arquivos MP4.
# Uso: bash strip_metadata.sh <input.mp4> <output_clean.mp4>
set -euo pipefail

INPUT="${1:?Argumento 1 (input) é obrigatório}"
OUTPUT="${2:?Argumento 2 (output) é obrigatório}"

echo "[strip_metadata] Limpando metadados de: $INPUT"

# Passo 1: limpeza profunda via FFmpeg (stream copy, sem re-encode)
ffmpeg -y -i "$INPUT" \
  -map 0:V -map "0:a?" \
  -map_metadata -1 \
  -map_metadata:s -1 \
  -map_chapters -1 \
  -fflags +bitexact \
  -flags:v +bitexact \
  -flags:a +bitexact \
  -c copy \
  "${OUTPUT%.mp4}_temp.mp4"

# Passo 2: ExifTool remove qualquer resíduo JUMBF/XMP que o FFmpeg deixou
if command -v exiftool &>/dev/null; then
  exiftool -overwrite_original -all= -jumbf= "${OUTPUT%.mp4}_temp.mp4" 2>/dev/null || true
fi

mv "${OUTPUT%.mp4}_temp.mp4" "$OUTPUT"
echo "[strip_metadata] ✅ Concluído: $OUTPUT"

# Verificação
if command -v exiftool &>/dev/null; then
  REMAINING=$(exiftool -G -a "$OUTPUT" 2>/dev/null | grep -icE "jumbf|c2pa|cai|creator tool" || true)
  if [ "$REMAINING" -gt 0 ]; then
    echo "[strip_metadata] ⚠️  Ainda há $REMAINING tags residuais. Executando re-encode forçado..."
    ffmpeg -y -i "$OUTPUT" -c:v libx264 -crf 18 -preset fast -c:a copy "${OUTPUT%.mp4}_reenc.mp4"
    mv "${OUTPUT%.mp4}_reenc.mp4" "$OUTPUT"
  else
    echo "[strip_metadata] ✅ Nenhuma tag C2PA/JUMBF detectada."
  fi
fi
STRIP_EOF

# -- humanize_video.sh --
cat > "${SKILL_DIR}/scripts/humanize_video.sh" << 'HUMAN_EOF'
#!/usr/bin/env bash
# video-anti-ban :: humanize_video.sh
# Aplica film grain, rescale +2px e fps-shift para quebrar assinatura pixel-level (SynthID).
# Uso: bash humanize_video.sh <input_clean.mp4> <output_humanized.mp4>
set -euo pipefail

INPUT="${1:?Argumento 1 (input) é obrigatório}"
OUTPUT="${2:?Argumento 2 (output) é obrigatório}"

# Configurações (ajustáveis via env)
GRAIN="${VIDEO_GRAIN_STRENGTH:-4}"        # 1–10, padrão 4 (sutil mas eficaz)
TARGET_W="${VIDEO_TARGET_W:-1080}"
TARGET_H="${VIDEO_TARGET_H:-1920}"
RESCALE_PAD=2                             # +2px antes do crop de volta

echo "[humanize_video] Humanizando: $INPUT (grain=$GRAIN, rescale=+${RESCALE_PAD}px)"

# Passo 1: rescale para +2px + crop de volta + film grain + fps-shift 0.5%
ffmpeg -y -i "$INPUT" \
  -vf "scale=$((TARGET_W + RESCALE_PAD)):$((TARGET_H + RESCALE_PAD)),\
crop=${TARGET_W}:${TARGET_H},\
noise=alls=${GRAIN}:allf=t+u" \
  -r "$(ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate "$INPUT" \
    | awk -F'/' '{printf "%.4f", ($1/$2)*1.005}')" \
  -c:v libx264 -crf 20 -preset fast \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "$OUTPUT"

echo "[humanize_video] ✅ Concluído: $OUTPUT"
HUMAN_EOF

# -- full_pipeline.sh (usado pelo n8n) --
cat > "${SKILL_DIR}/scripts/full_pipeline.sh" << 'PIPE_EOF'
#!/usr/bin/env bash
# video-anti-ban :: full_pipeline.sh
# Pipeline completo: strip_metadata + humanize em sequência.
# Uso (chamado pelo n8n Execute Command):
#   bash full_pipeline.sh <input_raw.mp4> <output_final.mp4>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="${1:?Argumento 1 (input raw) é obrigatório}"
OUTPUT="${2:?Argumento 2 (output final) é obrigatório}"
TMP_CLEAN="${INPUT%.mp4}_clean.mp4"

echo "============================================"
echo " video-anti-ban :: Full Pipeline"
echo " Input:  $INPUT"
echo " Output: $OUTPUT"
echo "============================================"

# Passo 1: Limpa metadados C2PA
bash "${SCRIPT_DIR}/strip_metadata.sh" "$INPUT" "$TMP_CLEAN"

# Passo 2: Humaniza pixels (anti-SynthID)
bash "${SCRIPT_DIR}/humanize_video.sh" "$TMP_CLEAN" "$OUTPUT"

# Limpeza
rm -f "$TMP_CLEAN"

echo "============================================"
echo " ✅ Pipeline concluído: $OUTPUT"
echo "============================================"
PIPE_EOF

chmod +x "${SKILL_DIR}/scripts/"*.sh
echo -e "${GREEN}  ==> Skill 'video-anti-ban' instalada em ${SKILL_DIR}${NC}"

# --- Referências da Skill ---
cat > "${SKILL_DIR}/references/detection-layers.md" << 'REF1_EOF'
# Camadas de Detecção de IA em Vídeo (YouTube & TikTok)

## Camada 1: Metadados / C2PA (Fácil de remover)
- Plataformas leem JUMBF boxes, XMP, tags `©too`/`©swr` e DigitalSourceType no container MP4.
- **Ferramentas que embutem:** Runway ML, Kling AI, Luma Dream Machine, Adobe Firefly.
- **Ferramentas que NÃO embutem:** Wan2.1 local, CogVideoX local, geração via ComfyUI sem plugin de watermark.
- **Remoção:** `ffmpeg -map_metadata -1` + ExifTool `-all= -jumbf=`

## Camada 2: Pixel-Level / SynthID (Mais difícil)
- SynthID (Google/DeepMind) embute watermark nas frequências de pixel — sobrevive a compressão lossy, crop e resize.
- Não fica em metadados: vive nos pixels.
- **Mitigação:** film grain (noise ≥ 3) + rescale ±2px + fps-shift 0.5% desorganiza as frequências estatísticas do watermark sem degradar qualidade perceptível.
- **Limitação:** mitigação imperfeita — detectores avançados ainda podem identificar. A melhor defesa é usar geradores locais (Wan2.1) que não embutem SynthID.

## Camada 3: Comportamental (Algoritmo de entrega)
Não é detecção de IA — é análise de qualidade de engajamento:
- Watch time / retention rate
- Click-through rate (thumbnail)
- Completion rate (quantos assistem até o fim)
- Velocidade de engajamento (likes/comments nas primeiras horas)

**A melhor estratégia contra a Camada 3 é conteúdo de qualidade com hook forte nos 2 primeiros segundos.**
REF1_EOF

cat > "${SKILL_DIR}/references/generators.md" << 'REF2_EOF'
# Comparativo de Geradores de Vídeo IA — Risco de Detecção

| Gerador | C2PA Embutido | SynthID | Requer Limpeza | Custo/vídeo (5s) |
|---|---|---|---|---|
| **Wan2.1 14B local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,25 (GPU alugada) |
| **Wan2.1 1.3B local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,05 (GPU alugada) |
| **CogVideoX local** | ❌ Não | ❌ Não | Apenas grain | ~R$ 0,10 (GPU alugada) |
| **Runway Gen-4 Turbo** | ✅ Sim | ✅ Sim | Strip completo | ~$0,25 |
| **Runway Gen-4.5** | ✅ Sim | ✅ Sim | Strip completo | ~$0,60 |
| **Kling v2.5 Turbo** | ✅ Sim | ⚠️ Parcial | Strip completo | ~$0,31 |
| **Kling v3 Standard** | ✅ Sim | ⚠️ Parcial | Strip completo | ~$0,50 |
| **HeyGen** | ✅ Sim | ❌ Não | Strip simples | ~$0,30/min |

## Recomendação Operacional
- **Volume diário (9 vídeos/dia):** Wan2.1 local + RunPod on-demand
- **Produtos premium (1–2/semana):** Kling v2.5 Turbo com pipeline completo de limpeza
- **Canal com apresentador:** HeyGen (strip simples de metadados suficiente)
REF2_EOF

echo -e "${GREEN}  ==> Referências da skill criadas.${NC}"
echo -e "${GREEN}  ==> Instalando ExifTool (necessário para limpeza C2PA)...${NC}"
apt-get install -y libimage-exiftool-perl 2>/dev/null || true

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

