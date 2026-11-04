# TikTok Shop Afiliados — Automação de Vídeos com IA Local

## 1. Visão Geral

- **Nicho:** Afiliado TikTok Shop — produtos com alta conversão (gadgets, beleza, casa, moda).
- **Formato:** Vídeos *faceless* verticais 9:16 (1080×1920), entre 20–45 segundos.
- **Voz:** Narração clonada via XTTS v2 (Docker local) ou fallback para Piper TTS `pt_BR-faber-medium`.
- **Roteiro:** Gerado pelo Ollama (Llama 3 8B) com prompt de gancho viral.
- **Pipeline:** Scraping do produto → Roteiro IA → Voz IA → B-roll + Legenda → Render → QA → Publicação.

## 2. Arquitetura do Pipeline

```
[Cron / Webhook n8n]
        │
        ▼
[1. Scraping do Produto]  ──→  Nome, preço, imagem, link afiliado
        │
        ▼
[2. Ollama Llama3:8b]     ──→  Roteiro de 30s com gancho viral
        │
        ▼
[3. XTTS v2 / Piper TTS]  ──→  Narração .mp3 / .wav
        │
        ▼
[4. Seleção de B-roll]    ──→  Vídeo de fundo (banco local ou produto)
        │
        ▼
[5. render_tiktok_video.py]  → Composição MoviePy: b-roll + áudio + legenda
        │
        ▼
[6. Aprovação Humana]     ──→  (via Telegram / painel Jeffrey)
        │
        ▼
[7. Publicação Playwright]  → Upload para TikTok Creator Studio
```

## 3. Serviços de IA Utilizados

| Serviço | Ferramenta | Endpoint | Custo |
|---|---|---|---|
| Geração de roteiro | Ollama + Llama 3 8B | `http://ollama:11434` | Gratuito (local) |
| Síntese de voz (principal) | XTTS v2 (Docker) | `http://xtts-api:5021/tts` | Gratuito (local) |
| Síntese de voz (fallback) | Piper TTS | binário local | Gratuito (local) |
| Renderização de vídeo | MoviePy + FFmpeg | script local | Gratuito |

## 4. Configuração de Volume de Conteúdo

- **Horários de publicação:** 08h, 14h, 20h (3 runs/dia via cron)
- **Produtos por run:** 3 vídeos
- **Máximo diário:** 9 vídeos (guardrail anti-shadowban)
- **Orçamento mensal:** R$ 30,00 (exclusivamente para VPS compartilhada)

## 5. Regras e Guardrails

1. **Disclosure obrigatório:** Toda legenda/descrição deve conter `#parceria` ou `Link na bio`.
2. **Aprovação humana:** Obrigatória durante a primeira semana. Após validação de qualidade, pode ser semi-autônomo.
3. **Anti-shadowban:** Máximo 9 vídeos/dia; variar horários e áudios de referência.
4. **Verificação de disponibilidade:** Checar se o produto ainda está ativo no TikTok Shop antes de publicar.
5. **Sem claims proibidos:** Nenhum roteiro pode fazer afirmações médicas, jurídicas ou de ganho garantido.

## 6. Arquivos do Negócio

```
businesses/tiktok-shop-afiliados/
├── assets/
│   └── voice_reference.wav        # Áudio de referência para clonagem de voz (XTTS)
├── content/
│   ├── scripts/                   # Roteiros gerados pelo Ollama (.txt)
│   ├── audio/                     # Narrações geradas (.mp3 / .wav)
│   ├── broll/                     # Vídeos de fundo (b-roll) organizados por categoria
│   ├── renders/                   # Vídeos finais renderizados (.mp4)
│   └── published/                 # Cópias dos vídeos já publicados
├── data/
│   └── products.json              # Cache de produtos minerados e seus links de afiliado
├── logs/
└── manifest.json                  # Config do template (gerado pelo provisioner)
```

## 7. Variáveis de Ambiente Necessárias

Adicionar ao `.env` da VPS:
```env
TIKTOK_SESSION_COOKIE=       # Cookie de sessão do TikTok Creator (renovar mensalmente)
XTTS_API_URL=http://xtts-api:5021/tts
XTTS_REFERENCE_AUDIO=/var/spirandeli/businesses/tiktok-shop-afiliados/assets/voice_reference.wav
TIKTOK_SHOP_MAX_VIDEOS_DAY=9
```

