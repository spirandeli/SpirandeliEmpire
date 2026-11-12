# Descoberta Dinâmica de Modelos (SpirandeliEmpire OS 3.2)

O `ModelDiscoveryService` ([discovery.py](file:///home/spira/spirandeliempire/backend/app/providers/discovery.py)) consulta os endpoints oficiais autenticados de cada provedor utilizando a API Key do próprio usuário:

- **Google Gemini:** `GET https://generativelanguage.googleapis.com/v1beta/models` com paginação `pageToken`. Modelos apenas de `embedContent` são marcados como `embeddings` e não aparecem como opções de chat.
- **OpenAI:** `GET https://api.openai.com/v1/models` com `Authorization: Bearer <API_KEY>` e enriquecimento por família oficial de modelos.
- **Anthropic Claude:** `GET https://api.anthropic.com/v1/models` com `x-api-key` e `anthropic-version: 2023-06-01`, paginação `after_id` e sinalização de modelos `deprecated` / `retired`.

## Cache e Resiliência
- Catálogos são armazenados por `(user_id, credential_id)` em `ai_models` com TTL configurável (`MODEL_CATALOG_CACHE_TTL_SECONDS=900`).
- Em caso de falha na sincronização, o último catálogo válido é preservado e o erro é registrado em `ai_provider_sync_logs`.

