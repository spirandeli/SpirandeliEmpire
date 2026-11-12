# Migração Segura de Credenciais Gemini e Remoção de Dependência Fixa (SpirandeliEmpire OS 3.2)

## Preservação da Chave Gemini Existente
Durante o startup (`seed_default_owner_if_needed`), o sistema verifica:
1. A tabela legada `integrations` (`id='gemini'`), descriptografando com compatibilidade Fernet.
2. Caso ausente, a variável de ambiente `GEMINI_API_KEY`.

Se uma chave válida for encontrada e a conta `ADMIN` ainda não possuir uma credencial `gemini` em `ai_provider_credentials`, a chave é re-criptografada com **AES-256-GCM** e associada ao `ADMIN` como `"Gemini Principal (Migrada)"`.
- A configuração original em `.env` e `integrations` **não é apagada nem sobrescrita**.
- O valor da chave nunca é impresso em logs ou exposto no frontend.

## Migração de Modelos
- Removida a obrigatoriedade de `gemini-2.5-flash` / `gemini-2.5-pro` nos agentes (`AgentDefinition.provider="dynamic"`, `model="dynamic"`) e configurações padrão.
- Todos os agentes passam a resolver dinamicamente seus modelos via `ModelRouter` conforme as preferências de cada usuário.

