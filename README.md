# SpirandeliEmpire OS 3.1
## LangGraph Edition — Autonomous AI Digital Company

O **SpirandeliEmpire OS 3.1** é uma empresa digital autônoma operada por 14 agentes de inteligência artificial especializados. O usuário atua como proprietário da empresa, enquanto **Jeffrey** atua como CEO e orquestrador principal, coordenando departamentos técnicos, de conteúdo e audiovisuais através de workflows duráveis com **LangGraph** e **Google Gemini API**.

---

## 🏛️ Os 14 Agentes Oficiais

1. **Jeffrey (CEO & Principal AI Engineer)**: Líder executivo, planejamento estratégico e orquestração supervisor.
2. **Fonseca (Frontend Engineer)**: Interfaces React, TypeScript, Tailwind CSS, Phaser 3 e PWA.
3. **Balsini (Backend Engineer)**: Arquitetura assíncrona FastAPI, Python 3.12, SQLAlchemy 2 e segurança.
4. **Jarvis (DevOps Engineer)**: Infraestrutura VPS, Docker Compose, Nginx, monitoramento e backups.
5. **Noé (Software Architect)**: Desenho de arquitetura, ADRs, modularização e contratos de API.
6. **Ford (Data Engineer)**: Modelagem relacional PostgreSQL, migrations com Alembic e Redis.
7. **Murphy (QA & Quality Gate Engineer)**: Validação de requisitos, suíte pytest e aprovação técnica.
8. **Script Agent (Content & Storytelling)**: Roteiros magnéticos para YouTube Shorts e TikTok.
9. **Voice Agent (Voice & Narration Specialist)**: Text-to-Speech (TTS), entonação e exportação de áudio.
10. **Subtitle Agent (Transcription & Subtitles)**: Whisper, legendas SRT e sincronismo milimétrico.
11. **Clipador Agent (Video Highlights Specialist)**: Identificação de ganchos e cortes virais de vídeos.
12. **News Agent (News & Trends Researcher)**: Monitoramento factual de RSS e tendências de mercado.
13. **Designer Agent (Visual Assets & Pixel Art)**: Thumbnails, capas e spritesheets em pixel art.
14. **Video Agent (Video Assembly & Render)**: Composição audiovisual com FFmpeg e exportação MP4.

---

## 🚀 Arquitetura Tecnológica

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL / SQLite, Redis, Celery.
- **Orquestrador de IA**: LangGraph (`StateGraph`, `checkpoints`, `interrupts`, `resume`, `subgraphs`).
- **Provedor de LLM**: Google Gemini API oficial (`google-genai`).
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Phaser 3, Lucide Icons.
- **PWA**: Mobile-first, Service Worker autônomo, manifest, responsividade e touch controls.
- **Escritório Virtual Pixel-Art**: Top-down 2D com 8 salas funcionais e avatares animados sincronizados com estados reais do backend.
- **Segurança**: Integration Hub com criptografia Fernet AES-256 em repouso.

---

## 💻 Como Executar

### 1. Execução Local Rápida (Desenvolvimento)

#### Backend:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Acesse a documentação da API em: `http://localhost:8000/docs`

#### Testes Automatizados (Quality Gate Murphy):
```bash
cd backend
uv run pytest
```

#### Frontend:
```bash
cd frontend
npm run dev
```
Acesse o aplicativo em: `http://localhost:5173`

---

### 2. Execução em Produção via Docker Compose

```bash
docker compose up -d --build
```
Acesse o portal completo em: `http://localhost:8080`

---

## 📊 Estrutura de Diretórios

```text
spirandeliempire/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # REST APIs & WebSockets
│   │   ├── core/              # Configurações & Segurança Fernet
│   │   ├── database/          # Modelos SQLAlchemy 2 e Sessão
│   │   ├── agents/            # Registry dos 14 agentes oficiais
│   │   ├── tools/             # Ferramentas reais com sandbox
│   │   ├── providers/         # Integração Gemini API oficial
│   │   ├── orchestrator/      # LangGraph StateGraph, nós e 5 grafos
│   │   ├── services/          # Camada de serviços da aplicação
│   │   └── workers/           # Celery background workers
│   ├── tests/                 # Suíte de testes com pytest
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── office/            # Escritório Pixel-Art Phaser 3
│   │   ├── dashboard/         # Métricas e monitor de VPS
│   │   ├── chat/              # Chat interativo com Jeffrey
│   │   ├── projects/          # Projects Hub & Wizard Novo Negócio
│   │   ├── agents/            # Painel dos 14 agentes
│   │   ├── workflows/         # Monitor de grafos e checkpoints
│   │   ├── approvals/         # Human-in-the-Loop
│   │   ├── integrations/      # Integration Hub
│   │   └── artifacts/         # Explorador de entregáveis
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   └── nginx/                 # Proxy reverso e streaming WS
├── docs/                      # Documentação técnica detalhada
├── docker-compose.yml
└── README.md
```

---

## 📄 Licença
Propriedade de **SpirandeliEmpire**. Todos os direitos reservados.

