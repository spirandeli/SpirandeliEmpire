# 11 — Auditoria do Frontend (SpirandeliEmpire OS 3.2)

**Data:** 2026-11-12

- **Telas v3.2 Verificadas no Código:**
  - [AuthView.tsx](file:///home/spira/spirandeliempire/frontend/src/auth/AuthView.tsx): Login, Cadastro, Esqueci minha senha e `FirstAccessSetupView` (troca obrigatória de senha).
  - [ProfileSecurityView.tsx](file:///home/spira/spirandeliempire/frontend/src/profile/ProfileSecurityView.tsx): Dados pessoais, alteração de senha, sessões ativas com revogação e painel administrativo.
  - [AIProvidersView.tsx](file:///home/spira/spirandeliempire/frontend/src/ai/AIProvidersView.tsx): Cadastro BYOK, mascaramento, teste de conexão, sincronização de modelos e revogação/exclusão.
  - [AIModelManagerView.tsx](file:///home/spira/spirandeliempire/frontend/src/ai/AIModelManagerView.tsx): Modelo padrão global, configuração dos 14 agentes, 11 perfis de tarefa, política de fallback, consumo de tokens e filtro `chatOnly=true` aplicado nos seletores de geração.
  - [api.ts](file:///home/spira/spirandeliempire/frontend/src/services/api.ts): Atualizado `changePassword()` para armazenar `access_token` renovado após a troca de senha.
- **Validação de Build e Tipagem:**
  - `cd frontend && npx tsc --noEmit`: `exit code 0`.
  - `cd frontend && npm run build`: `exit code 0` (`2116` módulos transformados, PWA `sw.js` e `manifest.webmanifest` gerados).

