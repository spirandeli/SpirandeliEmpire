# 02 — Auditoria do Backend, Banco de Dados e APIs

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 02 — FastAPI, PostgreSQL, Alembic, Redis/Celery, Autenticação/RBAC, Contratos Frontend/Backend e Testes.

---

## 1. Resumo Executivo

A auditoria do backend identificou lacunas críticas em **autenticação/autorização**, **migrations de banco de dados**, **persistência de usuários/memória/logs/execuções**, **despacho assíncrono via Celery/Redis**, **tratamento global de erros** e **segurança de downloads**. Todos os pontos dentro do escopo do Prompt 02 foram corrigidos e validados com suíte automatizada executada tanto em **SQLite** quanto em **PostgreSQL 16** e **Redis 7**.

---

## 2. Problemas Encontrados e Correções Aplicadas

### 2.1. FastAPI, Autenticação, Autorização e Segurança
- **Problema:** `backend/app/auth/` estava vazio; todos os endpoints `/api/v1/*` eram públicos; `CORS_ORIGINS` combinava `"*"` com `allow_credentials=True`; `ValueError` em `resume_workflow` / `decide_approval` gerava HTTP `500`; `artifacts/{id}/download` não validava se `file_path` estava dentro de `STORAGE_DIR`; `psutil.cpu_percent(interval=0.1)` bloqueava o event loop.
- **Correções:**
  - Criado sistema de autenticação JWT HS256 + hash PBKDF2-HMAC-SHA256 em [security.py](file:///home/spira/spirandeliempire/backend/app/auth/security.py) e dependências `get_current_user`, `require_role` e `seed_default_owner_if_needed` em [dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py).
  - Criados endpoints `/api/v1/auth/login`, `/api/v1/auth/register` e `/api/v1/auth/me` em [auth.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/auth.py).
  - Protegidos todos os endpoints em `agents.py`, `approvals.py`, `artifacts.py`, `chat.py`, `integrations.py`, `memory.py`, `projects.py`, `system.py`, `tasks.py`, `workflows.py` e validação opcional de `?token=` em `websocket.py`.
  - Removido `"*"` de `CORS_ORIGINS` em [config.py](file:///home/spira/spirandeliempire/backend/app/core/config.py).
  - Adicionados handlers globais de `ValueError` (HTTP `400`) e `Exception` (HTTP `500` + gravação em `SystemLogModel`) em [main.py](file:///home/spira/spirandeliempire/backend/app/main.py), além de `/health` verificando conectividade real com Banco e Redis.
  - Protegido `/api/v1/artifacts/{id}/download` com `Path.resolve().is_relative_to(settings.STORAGE_DIR.resolve())` (HTTP `403` fora do sandbox).
  - Alterado `psutil.cpu_percent(interval=None)` em [system_service.py](file:///home/spira/spirandeliempire/backend/app/services/system_service.py) para não bloquear o event loop.

### 2.2. PostgreSQL, Models e Alembic Migrations
- **Problema:** `backend/alembic/` estava vazio; faltavam modelos persistentes para `Users`, `WorkflowExecutions`, `Memory`, `SystemLogs` e `Settings`; `TaskModel.workflow_id`, `ArtifactModel.workflow_id` e `ApprovalModel.workflow_id` não tinham `ForeignKey`; `datetime.utcnow()` gerava warnings de depreciação.
- **Correções:**
  - Adicionados `UserModel`, `WorkflowExecutionModel`, `MemoryModel`, `SystemLogModel` e `SettingModel`, além de FKs e índices em [models.py](file:///home/spira/spirandeliempire/backend/app/database/models.py) e `utc_now()` timezone-aware.
  - Configurado pool de conexões (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`) para PostgreSQL em [session.py](file:///home/spira/spirandeliempire/backend/app/database/session.py).
  - Inicializado Alembic com [alembic.ini](file:///home/spira/spirandeliempire/backend/alembic.ini), [env.py](file:///home/spira/spirandeliempire/backend/alembic/env.py) e migration inicial [0001_initial.py](file:///home/spira/spirandeliempire/backend/alembic/versions/0001_initial.py).
  - Criado [memory/service.py](file:///home/spira/spirandeliempire/backend/app/memory/service.py) e endpoint `/api/v1/memory/` ([memory.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/memory.py)).
  - Adicionados CRUD completo de tarefas (`POST/GET/PATCH/DELETE /api/v1/tasks/`), atualização/exclusão de projetos (`PATCH/DELETE /api/v1/projects/{id}`), logs/settings (`/api/v1/system/logs`, `/api/v1/system/settings`) e paginação (`limit`/`offset`) + filtros nas listagens.

### 2.3. Redis, Celery Worker e Streaming de Eventos
- **Problema:** `WorkflowManager.start_workflow()` bloqueava requisições HTTP executando `graph.ainvoke()` inline; `celery_app.py` possuía apenas um stub `time.sleep(1)`; `EventSystem` era isolado em memória local do processo FastAPI.
- **Correções:**
  - Implementadas tasks reais `execute_workflow_task` e `resume_workflow_task` em [celery_app.py](file:///home/spira/spirandeliempire/backend/app/workers/celery_app.py) com lock distribuído no Redis (`workflow_lock:{workflow_id}`) para idempotência, `task_acks_late=True`, `autoretry_for=(ConnectionError, TimeoutError)`, `max_retries=2` e `task_time_limit=1800`.
  - Atualizado [manager.py](file:///home/spira/spirandeliempire/backend/app/orchestrator/workflows/manager.py) para despachar workflows assincronamente via Celery quando o broker Redis está disponível (retornando `status: "queued"` sem bloquear HTTP), registrar `WorkflowExecutionModel`, suportar cancelamento (`POST /api/v1/workflows/{id}/cancel`) e recuperação (`recover_stuck_workflows`).
  - Integrado Redis Pub/Sub (`spirandeli:events`) em [events/manager.py](file:///home/spira/spirandeliempire/backend/app/events/manager.py) para que workers publiquem eventos em tempo real para os WebSockets conectados.

### 2.4. Contratos Frontend / Backend
- **Correções:** Atualizado [api.ts](file:///home/spira/spirandeliempire/frontend/src/services/api.ts) para enviar header `Authorization: Bearer <token>`, suportar `login()`, tratar HTTP `401`/`204` e anexar `?token=` na URL WebSocket.

---

## 3. Evidências de Testes Executados

| Comando | Ambiente | Resultado |
| :--- | :--- | :--- |
| `DATABASE_URL="postgresql+asyncpg://..." uv run alembic upgrade head` | PostgreSQL 16.15 | **PASS** (`Running upgrade -> 0001_initial`) |
| `cd backend && uv run pytest -v` | SQLite (`aiosqlite`) | **PASS** (`18 passed in 2.24s`, 0 warnings) |
| `cd backend && DATABASE_URL="postgresql+asyncpg://..." uv run pytest -v` | PostgreSQL 16.15 + Redis 7 | **PASS** (`18 passed in 2.40s`, 0 warnings) |
| `CELERY_ALWAYS_EAGER=true uv run python -c "...execute_workflow_task.apply(...)..."` | Celery Worker (Eager) | **PASS** (`status: waiting_approval`) |
| `cd frontend && npx tsc --noEmit` | TypeScript 5.6.3 | **PASS** (exit code `0`) |

---

## 4. Status Final dos Requisitos do Prompt 02

| Requisito | Status | Observações |
| :--- | :---: | :--- |
| Inicialização FastAPI & OpenAPI | **PASS** | Lifespan inicializa DB, seeds e Redis Pub/Sub |
| Conexão PostgreSQL & Migrations Alembic | **PASS** | `alembic upgrade head` validado no PostgreSQL 16 |
| Conexão Redis & Celery Workers | **PASS** | Dispatch não-bloqueante, lock de idempotência, retry e cancelamento |
| Autenticação & Autorização (RBAC) | **PASS** | JWT HS256, `401` sem token, `403` para `viewer` em mutações |
| Persistência (Users, Memory, Logs, Settings, Executions) | **PASS** | Todos os 14 modelos validados com testes |
| Tratamento de Erros & Segurança de Download | **PASS** | `404` padronizado e bloqueio de path traversal (`403`) |
| Contratos Frontend/Backend (`api.ts`) | **PASS** | Compilação `tsc --noEmit` limpa |

