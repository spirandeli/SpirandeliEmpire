# 14 — Registro de Correções Realizadas (Auditoria v3.2)

**Data:** 2026-11-12

| # | Severidade | Arquivo | Problema | Correção |
| :---: | :---: | :--- | :--- | :--- |
| 1 | **P1** | [auth/dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py) | `get_current_user_allow_pw_change` não validava `UserSessionModel.is_revoked` para `sid` do JWT | Verificação de `UserSessionModel` (`is_revoked` e `expires_at`) a cada requisição |
| 2 | **P1** | [endpoints/auth.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/auth.py) | `logout()` só revogava sessão por cookie de refresh | Revogação adicional pelo `sid` do access token (Bearer ou Cookie) |
| 3 | **P1** | [endpoints/users.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/users.py), [api.ts](file:///home/spira/spirandeliempire/frontend/src/services/api.ts) | `change_password()` revogava todas as sessões sem emitir nova sessão ao usuário atual | Emite nova `UserSessionModel` + cookies + `access_token` na resposta; `api.ts` atualiza token local |
| 4 | **P1** | [endpoints/websocket.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/websocket.py) | `/api/v1/events` aceitava WebSocket sem token | Exige JWT válido (query ou cookie) e sessão ativa; fecha com `4401` caso contrário |
| 5 | **P1** | [endpoints/workflows.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/workflows.py) | IDOR em `GET /workflows/{id}/checkpoints` | Valida `wf.user_id == current_user.id` (`404` para terceiros) |
| 6 | **P2** | [agents/executor.py](file:///home/spira/spirandeliempire/backend/app/agents/executor.py), [tools/registry.py](file:///home/spira/spirandeliempire/backend/app/tools/registry.py) | `script_generator` ignorava `content_text` do `ModelRouter` | `executor.py` injeta `content_text` em `script_generator` e fallback usa `model_router` com `user_id` |
| 7 | **P2** | [AIModelManagerView.tsx](file:///home/spira/spirandeliempire/frontend/src/ai/AIModelManagerView.tsx) | Seletores de geração listavam modelos `embeddings` e `retired` | Adicionado `chatOnly=true` nos seletores de geração |
| 8 | **P2** | [deploy.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/deploy.sh) | `nginx` retornava `502` temporário após recriação de containers | Adicionado `docker compose restart nginx` após migrations |

