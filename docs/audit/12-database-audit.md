# 12 — Auditoria do Banco de Dados e Migrations

**Data:** 2026-11-12

- **Engine e ORM:** PostgreSQL 16 (`spirandeli-postgres`) + SQLAlchemy 2.0 (`sqlalchemy[asyncio]`, `asyncpg`, `greenlet`).
- **Migrations Alembic:**
  - `0001_initial.py`: Schema base (agentes, projetos, workflows, execuções, tarefas, artefatos, aprovações, integrações, eventos, chat, memória, logs, settings).
  - `0002_v32_multiuser_byok_models.py`: Tabelas v3.2 (`user_sessions`, `password_reset_tokens`, `invite_codes`, `security_audit_logs`, `ai_provider_credentials`, `ai_models`, `ai_provider_sync_logs`, `user_ai_preferences`, `agent_model_configs`, `task_model_configs`, `ai_usage_records`) e colunas de isolamento `user_id` + índices/foreign keys.
- **Verificação:** `alembic upgrade head` executado dentro de `spirandeli-backend` durante `./infrastructure/scripts/deploy.sh` com código de saída `0` e preservação integral dos dados existentes.

