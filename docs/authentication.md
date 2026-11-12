# Autenticação e Sessões (SpirandeliEmpire OS 3.2)

## Visão Geral
O sistema utiliza autenticação multiusuário baseada em **hash scrypt** para senhas, **JWT HS256 de curta duração** (30 min por padrão) para access tokens e **refresh tokens rotativos** armazenados em `user_sessions` (via cookies `HttpOnly`, `SameSite=Lax` e suporte a `Authorization: Bearer`).

## Fluxos Principais
- **Cadastro (`POST /api/v1/auth/register`):** Valida e-mail único, força de senha (mínimo 8 caracteres com letras e números), confirmação de senha e política administrativa (`public`, `invite_only`, `disabled`). Novos cadastros recebem sempre o papel `USER`.
- **Login (`POST /api/v1/auth/login`):** Autentica por e-mail ou usuário, aplica rate limiting por IP e bloqueio temporário progressivo após 5/10 falhas.
- **Refresh (`POST /api/v1/auth/refresh`):** Rotaciona o refresh token a cada uso e invalida tokens reutilizados.
- **Logout (`POST /api/v1/auth/logout`):** Revoga a sessão atual e limpa os cookies de autenticação.
- **Recuperação de Senha (`POST /api/v1/auth/forgot-password` e `/reset-password`):** Gera token temporário e revoga todas as sessões ativas após redefinição.
- **Sessões (`GET /api/v1/users/me/sessions`, `DELETE /api/v1/users/me/sessions/{id}`):** Permite listar e encerrar sessões ativas.

