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
