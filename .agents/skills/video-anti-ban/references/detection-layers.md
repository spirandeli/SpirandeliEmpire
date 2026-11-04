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
