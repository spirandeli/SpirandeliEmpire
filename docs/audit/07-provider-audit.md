# 07 — Auditoria dos Providers de IA (Gemini, OpenAI, Anthropic)

**Data:** 2026-11-12  
**Arquivo Principal:** [adapters.py](file:///home/spira/spirandeliempire/backend/app/providers/adapters.py)

| Provedor | Implementação | Credencial no Ambiente | Teste de Conexão | Catálogo | Geração | Classificação |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini** | `GeminiAdapter` (`v1beta/models`, paginação `pageToken`, `:generateContent`) | Sim (preservada na conta owner) | **PASS** ao vivo (`Connected`, `767ms`) | **PASS** ao vivo (`63` modelos, `438ms`) | Verificada em ciclos anteriores + mocks | **PASS** |
| **OpenAI** | `OpenAIAdapter` (`v1/models`, `OpenAI-Organization`, `v1/chat/completions`) | Não cadastrada no ambiente | Testado via mock | Testado via mock | Testado via mock | **BLOCKED (Live) / PASS (Code & Mock)** |
| **Anthropic Claude** | `AnthropicAdapter` (`v1/models`, headers `x-api-key` + `anthropic-version: 2023-06-01`, paginação `after_id`, lifecycle `retired`/`deprecated`, `v1/messages`) | Não cadastrada no ambiente | Testado via mock | Testado via mock | Testado via mock | **BLOCKED (Live) / PASS (Code & Mock)** |

- Tratamento HTTP padronizado em `_classify_http_error`: `400/401` (`Invalid Credential`), `403` (`Permission Denied`), `429` (`Rate Limited`), `5xx` (`Provider Unavailable`).

