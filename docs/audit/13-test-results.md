# 13 — Resultados dos Testes Executados

**Data:** 2026-11-12

## 1. Suíte Backend (`cd backend && uv run pytest -v`)
- **Resultado:** **31 passed in 12.11s** (0 falhas, 0 skipped, 0 warnings).
- **Cobertura:**
  - `test_agents.py` (2 testes): 14 agentes oficiais e salas.
  - `test_api.py` (4 testes): `/health`, `/agents`, `/system/metrics`, `/integrations`.
  - `test_backend_comprehensive.py` (7 testes): rejeição sem auth (`401`), login inválido, RBAC (`403`), CRUD projetos/tarefas, memória/logs/settings, bloqueio de download fora de `STORAGE_DIR`, workflow inline e cancelamento.
  - `test_langgraph_and_14_agents.py` (5 testes): execução individual dos 14 agentes, delegação paralela, substituição em falha, durabilidade `interrupt()`/restart/`resume`, rejeição humana e RBAC.
  - `test_tools.py` (5 testes): `system_monitor`, `file_writer`/`file_reader`, negação de permissão, bloqueio de traversal (`../.env`, `/etc/passwd`), `image_generator` PNG real e `tts_generator` `BLOCKED` explícito.
  - `test_v32_multiuser_byok.py` (6 testes): AES-256-GCM + rotação, cadastro/login/refresh/logout/reset, troca obrigatória de senha no primeiro acesso (incluindo revogação do token antigo e validade do novo), isolamento multiusuário, Model Discovery + precedência 5 níveis + fallback explícito (com mocks para OpenAI/Claude), e `test_session_revocation_and_checkpoint_idor`.
  - `test_workflows.py` (2 testes): supervisor e despacho assíncrono Celery.

## 2. Frontend (`cd frontend`)
- `npx tsc --noEmit`: **exit code 0**.
- `npm run build` (`tsc -b && vite build`): **exit code 0** (`2116` módulos, PWA `sw.js` gerado).

## 3. Testes Ao Vivo na Stack Docker (`http://localhost:8086`)
- `GET /health`: HTTP `200`, `{"status":"healthy","version":"3.2.0","dependencies":{"database":"ok","redis":"ok"}}`.
- **Gemini ao vivo (`owner@spirandeliempire.local`):** `test_credential` → `Connected` (`767ms`); `sync_models` → `63` modelos sincronizados (`438ms`).
- **Segurança ao vivo:** `GET /workflows/{id}/checkpoints` (`200` dono / `404` terceiro); WebSocket `/api/v1/events` sem token rejeitado (`InvalidStatus`) e com token válido (`ping`/`pong` OK); `logout` revogando token imediatamente (`401` em `/auth/me`).
- **Workflows Celery ao vivo:** `development` (`waiting_approval` → `resume` → `completed`, `5` tarefas visíveis em `/api/v1/tasks/`); `content` (`completed`, `tts_status: blocked`, sem `.wav` stub).

