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
