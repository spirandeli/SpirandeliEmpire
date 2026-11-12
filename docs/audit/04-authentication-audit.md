# 04 — Auditoria de Autenticação (SpirandeliEmpire OS 3.2)

**Data:** 2026-11-12

## Pontos Auditados
- **Cadastro (`POST /api/v1/auth/register`):** Valida formato de e-mail, unicidade (`409`), confirmação de senha, política de força (`>=8` letras+números), `accept_terms`, rate limit por IP (`10 req / 300s`), modos `public`, `invite_only` (`InviteCodeModel` uso único e expiração) e `disabled` (`403`). Role fixado em `"USER"` no backend (bloqueia auto-atribuição de `ADMIN`).
- **Login (`POST /api/v1/auth/login`):** Autentica contra hash `scrypt$16384$8$1` (compatível com `pbkdf2_sha256$`), bloqueio progressivo por conta (`60s` após 5 falhas, `5min` após 10 falhas com HTTP `429`) e rate limit por IP (`20 req / 60s`). Emite cookies `HttpOnly` + `SameSite=lax` (`spirandeli_access`, `spirandeli_refresh`) e tokens Bearer.
- **Sessões (`/refresh`, `/logout`, `/users/me/sessions`):** Rotação de refresh token (`refresh_token_hash` atualizado a cada refresh, invalidando o token anterior), listagem e revogação individual de sessões, e validação estrita de `sid` em `UserSessionModel` a cada requisição autenticada.
- **Recuperação de Senha (`/forgot-password`, `/reset-password`):** Token opaco de 48 bytes armazenado com SHA-256, expiração de 30 minutos, uso único (`used_at`) e revogação de todas as sessões ativas do usuário após redefinição.
- **Primeiro Acesso Administrativo:** `seed_default_owner_if_needed()` idempotente; `get_current_user()` bloqueia acesso às rotas normais com `403 PASSWORD_CHANGE_REQUIRED` enquanto `must_change_password=True`, exigindo senha `>=12` caracteres com maiúsculas, minúsculas, números e símbolo especial em `PATCH /api/v1/users/me/password`.

