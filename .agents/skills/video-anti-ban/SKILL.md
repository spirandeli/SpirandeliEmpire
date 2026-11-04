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
