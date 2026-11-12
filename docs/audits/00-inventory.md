# 00 — Inventário Geral e Diagnóstico do Sistema (SpirandeliEmpire OS 3.1)

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 01 — Diagnóstico exclusivo (somente leitura, sem alterações funcionais de código).  
**Workspace:** `/home/spira/spirandeliempire`

---

## 1. Diagnóstico Geral

O **SpirandeliEmpire OS 3.1** possui uma estrutura visual e estrutural avançada (FastAPI assíncrono, 5 grafos LangGraph compilados, 14 agentes definidos no Registry, escritório virtual 2D em Phaser 3 com spritesheets customizados, Docker Compose com 6 serviços rodando na porta `8086`). Contudo, a inspeção do código real revela que **a maior parte da inteligência autônoma e das integrações opera de forma simulada, hardcoded ou desconectada**:

1. **Agentes não executam LLM nos workflows:** Nos 5 grafos LangGraph (`jeffrey_supervisor_graph`, `development_graph`, `content_graph`, `clip_graph`, `business_graph`), apenas o nó `interpret_request_node` chama o `GeminiProvider`. Os demais 13 especialistas nunca invocam o LLM; eles gravam templates estáticos ou executam nós vazios (`no-op`).
2. **GeminiProvider em modo fallback offline:** Sem `GEMINI_API_KEY` configurada no `.env` e sem ler a chave salva no Integration Hub (banco de dados), o sistema cai silenciosamente em `_generate_intelligent_fallback()`, retornando respostas determinísticas pré-escritas.
3. **Human-in-the-Loop quebrado:** Nenhum grafo utiliza `langgraph.types.interrupt()`. Os nós de aprovação apenas marcam `waiting_for_approval = True` e avançam diretamente até `END`. O `resume_workflow` reinicia o grafo do `START`.
4. **Tool Registry incompleto e simulado:** Dos ~33+ nomes de ferramentas declarados nos 14 agentes em `OFFICIAL_AGENTS`, apenas **8 ferramentas** estão registradas em `backend/app/tools/registry.py`, sendo 4 delas simuladas (`web_search`, `script_generator`, `srt_formatter`, `tts_generator`).
5. **Workers, Migrations, Memória, Backup e Autenticação ausentes ou stubs:** O Celery worker (`heavy_render_job`) apenas executa `time.sleep(1)`; `backend/alembic/` está vazio; `backend/app/memory/` e `backend/app/auth/` estão vazios; não há scripts de backup/restore (`infrastructure/scripts/` vazio).

---

## 2. Arquitetura Encontrada

### 2.1. Stack Real Observada
- **Backend:** Python 3.12, FastAPI `>=0.115.0`, SQLAlchemy 2 (`>=2.0.36`, async), Pydantic v2, LangGraph `>=0.2.45` (`InMemorySaver`), `google-genai>=0.1.1`, Celery `>=5.4.0`, Redis `>=5.2.0`, `psutil`, `cryptography` (Fernet).
- **Banco de Dados:** SQLite (`spirandeliempire.db`) configurado como padrão em `.env.example` e `config.py`; PostgreSQL 16 Alpine e Redis 7 Alpine configurados no `docker-compose.yml`. Criação de tabelas feita via `Base.metadata.create_all` no `lifespan` de `backend/app/main.py` (sem Alembic).
- **Frontend:** React 18.3.1, TypeScript 5.6.3, Vite 5.4.10, Tailwind CSS 3.4.14, Phaser 3.87.0, `lucide-react`, `vite-plugin-pwa`.
- **Infraestrutura / Docker:** `docker-compose.yml` com 6 containers ativos (`spirandeli-postgres`, `spirandeli-redis`, `spirandeli-backend`, `spirandeli-worker`, `spirandeli-frontend`, `spirandeli-nginx` na porta `8086`).

### 2.2. Evidências de Execução Inicial (Baseline)
- **Backend `pytest`:** `cd backend && uv run pytest -v` → **10 passed, 12 warnings in 1.50s** (`test_agents.py`: 2, `test_api.py`: 4, `test_tools.py`: 3, `test_workflows.py`: 1).
- **Frontend TypeScript:** `cd frontend && npx tsc --noEmit` → **exit code 0** (sem erros de compilação).
- **Stack Docker (`http://localhost:8086`):** `curl http://localhost:8086/` retornou HTTP `200`; `curl http://localhost:8086/api/v1/agents/` retornou JSON com os 14 agentes.

---

## 3. Inventário Completo de Componentes

| Área | Caminho / Artefato | Estado Real Encontrado |
| :--- | :--- | :--- |
| **Backend Entrypoint** | `backend/app/main.py` | FastAPI + CORS + `lifespan` com `create_all` + seed de agentes e integrações. |
| **Config & Segurança** | `backend/app/core/config.py`, `security.py` | Pydantic Settings + Fernet AES. Possui chaves padrão hardcoded e `CORS_ORIGINS` com `"*"` + `allow_credentials=True`. |
| **Banco de Dados** | `backend/app/database/models.py`, `session.py` | 9 modelos (`AgentModel`, `ProjectModel`, `TaskModel`, `WorkflowModel`, `ArtifactModel`, `ApprovalModel`, `IntegrationModel`, `EventModel`, `ChatMessageModel`). Sem `MemoryModel` nem `UserModel`. |
| **Migrations** | `backend/alembic/` | **Diretório vazio.** Nenhuma migration Alembic existe. |
| **Auth** | `backend/app/auth/` | **Diretório vazio.** API 100% aberta sem autenticação. |
| **APIs v1** | `backend/app/api/v1/endpoints/*.py` | 10 routers (`agents`, `projects`, `tasks`, `workflows`, `artifacts`, `approvals`, `integrations`, `chat`, `system`, `websocket`). |
| **Agent Registry** | `backend/app/agents/registry.py` | 14 agentes oficiais definidos em `OFFICIAL_AGENTS` e persistidos em `agents` no startup. |
| **Tool Registry** | `backend/app/tools/registry.py` | Apenas 8 ferramentas registradas (`file_reader`, `file_writer`, `system_monitor`, `web_search`, `script_generator`, `srt_formatter`, `tts_generator`, `quality_scorer`). |
| **LangGraph** | `backend/app/orchestrator/graphs/*.py` | 5 grafos (`jeffrey_supervisor_graph`, `development_graph`, `content_graph`, `clip_graph`, `business_graph`). Todos usam `InMemorySaver()`. |
| **Checkpoints** | `backend/app/orchestrator/checkpoints/checkpoint_manager.py` | Salva snapshots resumidos em arquivos JSON em `storage/checkpoints/`. |
| **Workflow Manager** | `backend/app/orchestrator/workflows/manager.py` | Executa `await graph.ainvoke(...)` diretamente dentro da requisição HTTP (não usa Celery). |
| **Gemini Provider** | `backend/app/providers/gemini_provider.py` | Usa `google.genai.Client`, mas lê apenas `settings.GEMINI_API_KEY` / `os.environ` e cai em fallback estático se ausente. |
| **Integration Hub** | `backend/app/services/integration_service.py` | Encripta credenciais com Fernet. `test_connection` só testa `gemini`; os outros 5 provedores retornam sucesso fictício. |
| **Projects Hub** | `backend/app/services/project_service.py` | Cria projetos e wizard de negócios digitais no DB e dispara `workflow_manager.start_workflow`. |
| **Task Manager** | `backend/app/services/task_service.py` | Lista e atualiza `TaskModel`, mas nenhum workflow ou serviço cria registros em `tasks`. |
| **Artifact Manager** | `backend/app/services/artifact_service.py` | Lista, visualiza preview e faz download de arquivos salvos em disco. |
| **Event System** | `backend/app/events/manager.py` | Persiste `EventModel` no DB e faz broadcast para WebSockets em memória (não usa Redis Pub/Sub entre processos/workers). |
| **Memory System** | `backend/app/memory/` | **Diretório vazio.** Coluna `AgentModel.memory` nunca é lida ou escrita. |
| **Approvals** | `backend/app/services/approval_service.py` | Lista e decide aprovações, mas `resume_workflow` não retoma grafos pausados via `interrupt()`. |
| **Frontend Views** | `frontend/src/*` | 9 abas em `App.tsx` (`office`, `dashboard`, `chat`, `projects`, `agents`, `workflows`, `approvals`, `integrations`, `artifacts`). Sem tela `tasks`. |
| **Escritório Phaser 3** | `frontend/src/office/OfficeScene.ts`, `VirtualOffice.tsx` | Mapa 58x38 tiles, A* pathfinding, 14 spritesheets carregados, HUD de salas, Reunião Geral e drawer de agente conectados via WebSocket. |
| **PWA** | `frontend/vite.config.ts`, `frontend/public/` | `vite-plugin-pwa` gera `sw.js` e `manifest.webmanifest`, mas os ícones `pwa-192x192.png`, `pwa-512x512.png`, `apple-touch-icon.png`, `favicon.ico` e `robots.txt` **não existem** em `frontend/public/`. |
| **Workers** | `backend/app/workers/celery_app.py` | Celery configurado com Redis, mas apenas uma task stub `heavy_render_job` com `time.sleep(1)`, nunca chamada pela API. |
| **Infraestrutura** | `docker-compose.yml`, `infrastructure/` | Nginx proxy reverso configurado. `infrastructure/docker/`, `infrastructure/monitoring/`, `infrastructure/scripts/` estão **vazios**. |
| **Testes** | `backend/tests/*.py`, `tests/` | 10 testes unitários/API básicos em `backend/tests/`. Diretório raiz `tests/` está **vazio**. Sem testes E2E ou de frontend. |
| **Documentação** | `README.md`, `docs/*.md` | Documentação descreve arquitetura idealizada (ex.: Alembic, porta `8080`, ferramentas reais) que diverge do código atual. |

### Diretórios Vazios / Desconectados Identificados
- `backend/alembic/`
- `backend/app/approvals/`, `backend/app/artifacts/`, `backend/app/auth/`, `backend/app/departments/`, `backend/app/integrations/`, `backend/app/memory/`, `backend/app/projects/`, `backend/app/tasks/` (a lógica foi colocada em `backend/app/services/` e `endpoints/`, deixando esses diretórios vazios)
- `backend/app/orchestrator/nodes/`, `backend/app/orchestrator/routing/`
- `frontend/src/app/`, `frontend/src/assets/animations/`, `frontend/src/assets/maps/`, `frontend/src/assets/sprites/`, `frontend/src/assets/tiles/`, `frontend/src/departments/`, `frontend/src/hooks/`, `frontend/src/pwa/`
- `infrastructure/docker/`, `infrastructure/monitoring/`, `infrastructure/scripts/`
- `tests/` (raiz)

---

## 4. Matriz de Comparação: Implementação vs. Requisitos

| Módulo | Implementado | Integrado | Testado | Status |
| :--- | :---: | :---: | :---: | :--- |
| Jeffrey | Parcial | Parcial | Parcial | **FAIL** |
| Agent Registry | Sim | Sim | Sim | **PASS** |
| 14 agentes | Parcial | Parcial | Parcial | **FAIL** |
| LangGraph | Parcial | Parcial | Parcial | **FAIL** |
| Gemini | Parcial | Não | Não | **FAIL** |
| Tool Registry | Parcial | Parcial | Parcial | **FAIL** |
| Task Manager | Parcial | Não | Não | **FAIL** |
| Workflow Manager | Parcial | Parcial | Parcial | **FAIL** |
| PostgreSQL | Sim | Parcial | Não | **NOT VERIFIED** |
| Redis | Sim | Parcial | Não | **NOT VERIFIED** |
| Integration Hub | Parcial | Não | Parcial | **FAIL** |
| Projects Hub | Sim | Parcial | Não | **NOT VERIFIED** |
| Artifact Manager | Sim | Parcial | Não | **NOT VERIFIED** |
| Memory System | Não | Não | Não | **NOT IMPLEMENTED** |
| Approvals | Parcial | Não | Não | **FAIL** |
| Event System | Sim | Parcial | Não | **NOT VERIFIED** |
| Dashboard | Parcial | Parcial | Não | **FAIL** |
| Chat Jeffrey | Parcial | Parcial | Não | **FAIL** |
| Escritório 2D | Sim | Parcial | Não | **NOT VERIFIED** |
| PWA | Parcial | Não | Não | **FAIL** |
| Docker | Sim | Sim | Parcial | **PASS** |
| Workers | Parcial | Não | Não | **FAIL** |
| Backup e Restore | Não | Não | Não | **NOT IMPLEMENTED** |
| Testes | Parcial | Parcial | Sim | **FAIL** |

---

## 5. Problemas Arquiteturais Encontrados

1. **Execução bloqueante em requisições HTTP:** `WorkflowManager.start_workflow()` executa `await graph.ainvoke(...)` dentro do endpoint HTTP (`POST /workflows/start`, `POST /projects/`, `POST /chat/message`), em vez de enfileirar no Celery worker.
2. **Estado LangGraph efêmero (`InMemorySaver`)**: Todos os 5 grafos compilam com `InMemorySaver()`. Ao reiniciar o container `backend`, todo o histórico de execução dos grafos é perdido.
3. **Desconexão Integration Hub → GeminiProvider:** Salvar a chave da API Gemini via UI (`IntegrationModel`) não atualiza o singleton `gemini_provider`, que continua sem chave até que `.env` seja editado e o container reiniciado.
4. **Task Manager órfão:** `TaskModel` e `GET /api/v1/tasks/` existem, mas nenhum workflow cria tarefas no banco. Além disso, `DashboardView.tsx` tenta navegar para `onNavigate('tasks')`, rota inexistente em `App.tsx`.
5. **Agentes sem ferramentas reais:** Dos ~33+ tools listados em `OFFICIAL_AGENTS`, ~25 não possuem definição nem executor em `tools/registry.py`. Em `clip_graph.py`, `clip_extraction_node` chama `file_writer` como `clipador_agent`, mas `clipador_agent` não está em `authorized_agents` — falhando silenciosamente.
6. **Estados de agentes não persistidos:** `AgentModel.operational_state`, `metrics` e `history` nunca são atualizados pelos grafos durante a execução.
7. **EventSystem isolado por processo:** `EventSystem` mantém `_active_connections` em memória local do processo FastAPI; se um worker Celery publicar eventos, o WebSocket não receberá (falta Redis Pub/Sub).
8. **Tratamento de erros ausente em endpoints:** `resume_workflow` e `decide_approval` lançam `ValueError` sem capturar para retornar `404`, gerando HTTP `500`.

---

## 6. Simulações, Dados Hardcoded e Falsos Estados Detectados

- **`backend/app/providers/gemini_provider.py` (`_generate_intelligent_fallback`):** Retorna respostas pré-fabricadas por palavras-chave quando `GEMINI_API_KEY` não está ativa.
- **`backend/app/tools/registry.py`:**
  - `_web_search_executor`: Retorna resultados fictícios hardcoded (`https://news.spirandeliempire.internal/trends`).
  - `_script_generator_executor`: Escreve um template fixo de roteiro sem chamar LLM.
  - `_audio_inspector_executor` (`tts_generator`): Grava apenas um cabeçalho RIFF WAV vazio de 44 bytes (sem áudio real).
  - `_srt_formatter_executor`: Usa 4 linhas hardcoded se `lines` não for passado.
- **`backend/app/workers/celery_app.py` (`heavy_render_job`):** Apenas `time.sleep(1)` retornando `"rendered": True`.
- **`backend/app/orchestrator/graphs/*.py`:**
  - `content_graph.py`: `video_assembly_node` grava um JSON `.mp4.meta` simulado; `visual_generation_node` grava um SVG fixo; `content_strategy_node` e `script_review_node` são vazios.
  - `clip_graph.py`: `clipador_node` retorna 2 clipes hardcoded; `video_input_node`, `transcript_analysis_node`, `candidate_clips_node`, `rendering_node` são vazios.
  - `development_graph.py` e `business_graph.py`: Nós geram arquivos `.md`/`.py`/`.tsx`/`.sql`/`.html` estáticos sem LLM e possuem vários nós vazios.
- **`backend/app/services/integration_service.py`:** `test_connection` para `github`, `youtube`, `comfyui`, `websearch`, `tts` sempre retorna `success: True` sem fazer nenhuma chamada externa.
- **`frontend/src/dashboard/DashboardView.tsx`:** Card "Agentes Oficiais" exibe o número estático `14` hardcoded (linha 125).
- **`frontend/src/workflows/WorkflowsView.tsx`:** Sempre exibe `(Aprovado)` ao lado do score de QA (linha 106), ignorando `passed === false`.

---

## 7. Segurança, Desempenho e Dependências

### Segurança
- **P0 — Ausência total de autenticação:** Qualquer cliente na rede pode acessar `/api/v1/*`, ler/alterar chaves no Integration Hub, disparar workflows e baixar arquivos.
- **P0 — Path traversal / Leitura irrestrita em `file_reader` e `file_writer` (`tools/registry.py`):** A validação `startswith("/home/spira/spirandeliempire")` sem delimitador de diretório permite ler `.env` (segredos) e sobrescrever código-fonte da aplicação.
- **P1 — CORS inseguro (`main.py` / `config.py`):** `allow_credentials=True` combinado com `"*"` em `CORS_ORIGINS`.
- **P1 — Chaves padrão hardcoded:** `SECRET_KEY` e `ENCRYPTION_MASTER_KEY` possuem valores padrão fixos em `config.py`, `docker-compose.yml` e `.env.example`.

### Desempenho
- Execução síncrona de workflows LangGraph dentro de rotas HTTP FastAPI bloqueia a resposta ao usuário.
- `psutil.cpu_percent(interval=0.1)` em `system_service.py` bloqueia o event loop assíncrono por 100ms a cada requisição `/system/metrics`.

### Dependências
- `backend/pyproject.toml` usa `google-genai>=0.1.1`, `langgraph>=0.2.45` e `fastapi>=0.115.0` sem pinagem exata de versão (apenas `uv.lock`).
- `frontend/package.json` usa `lucide-react: ^1.16.0`, `phaser: ^3.87.0`, `vite-plugin-pwa: ^0.20.5`; o build PWA referencia ícones ausentes em `public/`.

---

## 8. Plano de Correção Priorizado

### P0 — Crítico (Segurança, Perda de Dados, Indisponibilidade)
1. Implementar autenticação/autorização básica (API Key / JWT) protegendo rotas administrativas e Integration Hub.
2. Restringir `file_reader` e `file_writer` estritamente ao sandbox `STORAGE_DIR` usando `Path.resolve().is_relative_to(...)` e remover valores padrão de chaves secretas em produção.
3. Configurar Alembic (`backend/alembic/`) com migration inicial reproduzível para PostgreSQL e SQLite.

### P1 — Funcionalidade Central Quebrada
4. Conectar `GeminiProvider` à chave encriptada salva no `IntegrationModel` (Integration Hub) em tempo de execução e remover fallback silencioso quando em modo real.
5. Substituir `InMemorySaver()` por checkpointer persistente (PostgreSQL/SQLite) e implementar `langgraph.types.interrupt()` + `Command(resume=...)` para Human-in-the-Loop real.
6. Fazer os nós dos 5 grafos LangGraph realmente invocarem o LLM (com o `system_prompt` de cada um dos 14 agentes) e persistirem `TaskModel` e `AgentModel.operational_state`.
7. Mover a execução de workflows para o worker Celery assíncrono com Redis Pub/Sub conectado ao `EventSystem`.
8. Implementar executores reais (ou erro explícito `NOT IMPLEMENTED` / integração real) para as ferramentas do `ToolRegistry` e corrigir permissões de `clipador_agent`, `designer_agent` e `video_agent`.

### P2 — Funcionalidade Parcial / Qualidade
9. Implementar testes reais em `IntegrationService.test_connection()` para GitHub, YouTube, ComfyUI, WebSearch e TTS.
10. Corrigir bugs de frontend: adicionar rota/aba `tasks` (ou corrigir card no `DashboardView`), buscar contagem dinâmica de agentes, corrigir label `(Aprovado)` condicional no `WorkflowsView` e adicionar ícones PWA ausentes (`pwa-192x192.png`, `pwa-512x512.png`).
11. Implementar `MemoryModel` / serviço de memória persistente em `backend/app/memory/` e scripts de Backup/Restore em `infrastructure/scripts/`.

### P3 — Melhoria Visual, Manutenção e Otimização
12. Remover diretórios vazios não utilizados ou consolidar módulos neles, atualizar `datetime.utcnow()` para `datetime.now(timezone.utc)` (eliminando os 12 warnings do pytest) e sincronizar `docs/` com a implementação real.

