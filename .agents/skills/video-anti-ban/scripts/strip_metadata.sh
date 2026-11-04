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
