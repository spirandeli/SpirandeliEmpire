# 01 — Inventário Completo da Arquitetura (SpirandeliEmpire OS 3.2)

**Data:** 2026-11-12  
**Workspace:** `/home/spira/spirandeliempire`  
**Branch Git:** `main` (alterações locais em `.env.example` e remoção prévia de legado `backend-python/`)  
**Ambiente:** Stack Docker em `http://localhost:8086` (`spirandeli-nginx`, `spirandeli-frontend`, `spirandeli-backend`, `spirandeli-worker`, `spirandeli-postgres`, `spirandeli-redis`). `.env` presente na raiz (conteúdo não exposto).

---

## 1. Backend (`backend/app/`)
- **Framework e Versão:** FastAPI (`fastapi>=0.115.0`), Python 3.12 (`pyproject.toml`, `SpirandeliEmpire OS v3.2.0`).
- **Entrypoint e Middlewares:** [main.py](file:///home/spira/spirandeliempire/backend/app/main.py) com `lifespan` (cria tabelas faltantes, executa `seed_default_owner_if_needed`, `seed_agents_if_needed`, `seed_integrations_if_needed`, inicia listener Redis Pub/Sub), `CORSMiddleware` com origens explícitas, handlers globais para `ValueError` (`400`) e `Exception` (`500` com log em `SystemLogModel`), e `/health` verificando PostgreSQL (`SELECT 1`) e Redis (`PING`).
- **Roteamento (`/api/v1`):** [api.py](file:///home/spira/spirandeliempire/backend/app/api/v1/api.py) agrega 17 módulos:
  - `auth` (`/auth`), `users` (`/users`), `ai_providers` (`/ai-providers`), `ai_models` (`/ai-models`), `ai_settings` (`/ai-settings`), `ai_usage` (`/ai-usage`), `agents` (`/agents`), `projects` (`/projects`), `tasks` (`/tasks`), `workflows` (`/workflows`), `artifacts` (`/artifacts`), `approvals` (`/approvals`), `integrations` (`/integrations`), `chat` (`/chat`), `memory` (`/memory`), `system` (`/system`), `websocket` (`/events`).
- **Autenticação & Autorização:** [auth/security.py](file:///home/spira/spirandeliempire/backend/app/auth/security.py) (hash `scrypt$16384$8$1` com compatibilidade `pbkdf2_sha256$`, tokens opacos SHA-256, JWT HS256), [auth/dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py) (`get_current_user_allow_pw_change`, `get_current_user` bloqueando `must_change_password`, `require_role`), [auth/rate_limit.py](file:///home/spira/spirandeliempire/backend/app/auth/rate_limit.py) (janela deslizante em memória).
- **Criptografia de Credenciais:** [core/security.py](file:///home/spira/spirandeliempire/backend/app/core/security.py) (`AES-256-GCM` com prefixo `gcm:<version>:<nonce>:<ct>` e AAD versionado, rotação com `PREVIOUS_ENCRYPTION_MASTER_KEY`, compatibilidade `Fernet` legado, `mask_secret`).

## 2. Frontend (`frontend/src/`)
- **Framework e Versão:** React `18.3.1`, TypeScript `5.6.3`, Vite `5.4.10`, TailwindCSS `3.4.14`, Phaser `3.87.0`, `vite-plugin-pwa` `0.20.5` ([package.json](file:///home/spira/spirandeliempire/frontend/package.json)).
- **Páginas/Views:** [App.tsx](file:///home/spira/spirandeliempire/frontend/src/App.tsx) controla sessão via `/api/v1/auth/me`, obriga `FirstAccessSetupView` quando `must_change_password=true`, conecta WebSocket `liveEvents` após autenticação e renderiza 14 abas (`VirtualOffice`, `DashboardView`, `ChatView`, `ProjectsView`, `TasksView`, `AgentsView`, `WorkflowsView`, `ApprovalsView`, `ArtifactsView`, `AIProvidersView`, `AIModelManagerView`, `ProfileSecurityView`, `IntegrationsView`, além de `ErrorBoundary`).
- **Cliente HTTP:** [services/api.ts](file:///home/spira/spirandeliempire/frontend/src/services/api.ts) com envio de cookies (`credentials: 'include'`) e suporte a Bearer token / refresh automático.

## 3. Banco de Dados & Migrations
- **Banco e ORM:** PostgreSQL 16 (`asyncpg>=0.30.0`) em produção/Docker; SQLite (`aiosqlite`) suportado em testes; SQLAlchemy 2.0 (`sqlalchemy[asyncio]>=2.0.36`, `greenlet>=3.1.0`).
- **Migrations Alembic:** [0001_initial.py](file:///home/spira/spirandeliempire/backend/alembic/versions/0001_initial.py) e [0002_v32_multiuser_byok_models.py](file:///home/spira/spirandeliempire/backend/alembic/versions/0002_v32_multiuser_byok_models.py).
- **Entidades (25 models em [models.py](file:///home/spira/spirandeliempire/backend/app/database/models.py)):**
  - *Auth & Segurança:* `UserModel`, `UserSessionModel`, `PasswordResetTokenModel`, `InviteCodeModel`, `SecurityAuditLogModel`.
  - *BYOK & AI Manager:* `AIProviderCredentialModel`, `AIModelCatalogModel`, `AIProviderSyncLogModel`, `UserAIPreferenceModel`, `AgentModelConfigModel`, `TaskModelConfigModel`, `AIUsageRecordModel`.
  - *Operação & LangGraph:* `AgentModel`, `ProjectModel`, `WorkflowModel`, `WorkflowExecutionModel`, `TaskModel`, `ArtifactModel`, `ApprovalModel`, `IntegrationModel`, `EventModel`, `ChatMessageModel`, `MemoryModel`, `SystemLogModel`, `SettingModel`.

## 4. Inteligência Artificial & LangGraph
- **Providers & Adaptadores:** [providers/base.py](file:///home/spira/spirandeliempire/backend/app/providers/base.py), [providers/adapters.py](file:///home/spira/spirandeliempire/backend/app/providers/adapters.py), [providers/gemini_provider.py](file:///home/spira/spirandeliempire/backend/app/providers/gemini_provider.py).
- **Discovery & Resolution:** [providers/discovery.py](file:///home/spira/spirandeliempire/backend/app/providers/discovery.py), [providers/model_resolver.py](file:///home/spira/spirandeliempire/backend/app/providers/model_resolver.py).
- **Agentes & Tools:** 14 agentes em [agents/registry.py](file:///home/spira/spirandeliempire/backend/app/agents/registry.py), execução via [agents/executor.py](file:///home/spira/spirandeliempire/backend/app/agents/executor.py) e ferramentas em [tools/registry.py](file:///home/spira/spirandeliempire/backend/app/tools/registry.py).
- **Grafos LangGraph:** `jeffrey_supervisor_graph.py`, `development_graph.py`, `content_graph.py`, `clip_graph.py`, `business_graph.py` com checkpointing em [persistent_saver.py](file:///home/spira/spirandeliempire/backend/app/orchestrator/checkpoints/persistent_saver.py).

## 5. Infraestrutura & Riscos Identificados na Inspeção Inicial
- **Containers:** `nginx` (`8086:80`), `frontend`, `backend`, `worker` (Celery + Redis), `postgres` (`127.0.0.1:5432`), `redis` (`127.0.0.1:6379`).
- **Scripts:** [deploy.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/deploy.sh), [backup.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/backup.sh), [restore.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/restore.sh).
- **Risco Inicial Detectado (para auditoria na Fase 2):** `get_current_user_allow_pw_change()` em [auth/dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py) valida assinatura/expiração do JWT, mas **não verifica se o `sid` da sessão continua ativo (não revogado) em `UserSessionModel`**, permitindo uso de access token após logout/revogação até o vencimento de 30 minutos.

