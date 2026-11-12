# 03 — Auditoria de Segurança (SpirandeliEmpire OS 3.2)

**Data:** 2026-11-12

## Vulnerabilidades Identificadas e Corrigidas
1. **[P1] Reuso de Access Token após Logout/Revogação de Sessão:**
   - **Causa:** `get_current_user_allow_pw_change()` em [dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py) validava apenas assinatura e `exp` do JWT, ignorando `UserSessionModel.is_revoked` para `payload["sid"]`. Além disso, `logout()` em [auth.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/auth.py) só revogava sessão por cookie de refresh.
   - **Correção:** `get_current_user_allow_pw_change()` passa a consultar `UserSessionModel` pelo `sid` e rejeitar com `401` sessões revogadas ou expiradas; `logout()` revoga também pelo `sid` do JWT Bearer/Cookie; `change_password()` em [users.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/users.py) revoga sessões antigas e emite nova sessão ativa.
   - **Verificação:** `test_session_revocation_and_checkpoint_idor` (`pytest`) e teste ao vivo em `http://localhost:8086` (`401` após `logout`).
2. **[P1] WebSocket `/api/v1/events` sem autenticação obrigatória:**
   - **Causa:** [websocket.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/websocket.py) aceitava conexões sem `?token=` quando o parâmetro era omitido.
   - **Correção:** Exige JWT válido (query `token` ou cookie `spirandeli_access`) e sessão `sid` ativa; caso contrário fecha com `code=4401`.
   - **Verificação:** Teste ao vivo com `websockets.connect` sem token (`InvalidStatus`) e com token válido (`ping`/`pong` OK).
3. **[P1] IDOR em Checkpoints de Workflow:**
   - **Causa:** `GET /api/v1/workflows/{workflow_id}/checkpoints` em [workflows.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/workflows.py) não validava `wf.user_id == current_user.id`.
   - **Correção:** Adicionada validação de propriedade (`404` quando pertence a outro usuário).
   - **Verificação:** `test_session_revocation_and_checkpoint_idor` e teste ao vivo (`200` dono, `404` terceiro).
4. **[P1] Sandbox de Ferramentas (já remediado no ciclo anterior e revalidado):**
   - `file_reader` e `file_writer` restritos a `settings.STORAGE_DIR.resolve()` via `is_relative_to`.
   - **Verificação:** `test_tool_sandbox_blocks_traversal_and_external_paths` bloqueia `../.env`, `../../etc/passwd` e `/etc/passwd`.

