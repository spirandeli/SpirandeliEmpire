# Bootstrap Administrativo e Primeiro Acesso (SpirandeliEmpire OS 3.2)

## Provisionamento via Variáveis de Ambiente
Configure no `.env` (sem versionar senhas reais no Git):
```env
INITIAL_ADMIN_EMAIL=spirandelidev@gmail.com
INITIAL_ADMIN_PASSWORD=<senha_provisoria>
INITIAL_ADMIN_NAME=Proprietário / Administrador Principal
```

No startup da aplicação (`seed_default_owner_if_needed` em [dependencies.py](file:///home/spira/spirandeliempire/backend/app/auth/dependencies.py)):
- Cria a conta `ADMIN` somente se ainda não existir.
- Nunca sobrescreve senha de conta já existente.
- Define `must_change_password=True`.

## Primeiro Acesso Obrigatório
1. Faça login com o e-mail administrativo e a senha provisória.
2. O sistema exibirá a tela **Configuração Inicial de Segurança**, bloqueando o acesso às demais APIs até a troca de senha.
3. Defina uma nova senha forte com **no mínimo 12 caracteres** (maiúsculas, minúsculas, números e símbolo).
4. Todas as sessões anteriores são invalidadas automaticamente após a troca.
5. Para recuperar acesso administrativo caso necessário, utilize o fluxo `/auth/forgot-password` ou redefina via script administrativo seguro no servidor.

