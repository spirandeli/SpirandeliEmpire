# AI Providers Hub — BYOK (SpirandeliEmpire OS 3.2)

## Provedores Suportados
1. **Google Gemini** (`gemini`)
2. **OpenAI** (`openai`, com suporte opcional a `OpenAI-Organization`)
3. **Anthropic Claude** (`anthropic`)

## Operações Disponíveis (`/api/v1/ai-providers/`)
- **Adicionar Conexão (`POST /connections`):** Permite múltiplas conexões por provedor (ex.: conta pessoal e conta produção).
- **Testar Conexão (`POST /connections/{id}/test`):** Recupera a chave criptografada no backend, executa validação autenticada de listagem (sem chamadas pagas de geração), mede latência e atualiza o status (`Connected`, `Invalid Credential`, `Permission Denied`, `Rate Limited`, `Provider Unavailable`, `Configuration Required`, `Connection Error`).
- **Atualizar / Revogar / Excluir (`PATCH`, `POST /revoke`, `DELETE`):** Chaves salvas são exibidas apenas de forma mascarada (`sk-****1234`) e nunca retornadas em texto claro pela API.

