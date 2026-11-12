# 05 — Auditoria de Isolamento Multiusuário (SpirandeliEmpire OS 3.2)

**Data:** 2026-11-12

## Evidências de Isolamento por `user_id`
- **Credenciais e Catálogo BYOK (`/api/v1/ai-providers/*`, `/api/v1/ai-models/*`, `/api/v1/ai-settings/*`, `/api/v1/ai-usage/*`):** Todas as consultas filtram por `user_id == current_user.id`; acesso a `connection_id` ou `model_record_id` de outro usuário retorna `404`.
- **Projetos, Tarefas, Workflows, Aprovações, Artefatos, Chat e Memória:** Filtrados por `user_id == current_user.id`. Subgrafos `development_graph`, `content_graph`, `clip_graph` e `business_graph` propagam `user_id` de `execution_context` para `agent_executor.execute_task(...)`, garantindo que `TaskModel` e `ModelRouter` operem exclusivamente no escopo do usuário dono do workflow.
- **Checkpoints & WebSocket:** Corrigidos nesta auditoria para exigir propriedade (`wf.user_id == current_user.id`) em `GET /workflows/{id}/checkpoints` e JWT + sessão ativa no WebSocket `/events`.
- **Administração (`/api/v1/users/admin/*`):** Protegida por `require_role("ADMIN")`; usuário `USER` recebe `403`. Administradores gerenciam usuários, papéis e políticas sem acesso ao valor descriptografado das API keys dos usuários.

