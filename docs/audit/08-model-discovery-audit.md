# 08 — Auditoria do Model Discovery

**Data:** 2026-11-12  
**Arquivos:** [discovery.py](file:///home/spira/spirandeliempire/backend/app/providers/discovery.py), [ai_models.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/ai_models.py)

- **Sincronização por credencial e usuário:** `ModelDiscoveryService.sync_models(user_id, credential_id)` valida ownership da credencial, respeita TTL de cache (`MODEL_CATALOG_CACHE_TTL_SECONDS=900` quando `force=False`), persiste em `AIModelCatalogModel` e registra histórico em `AIProviderSyncLogModel`.
- **Preservação em falha:** Em erro de rede ou HTTP do provedor, grava `status="error"` no log e mantém intacto o último catálogo válido no PostgreSQL.
- **Lifecycle e exclusão:** Modelos ausentes da listagem atual são marcados como `is_available=False, lifecycle_status="unconfirmed"` (sem perda de referência). `retired` recebe `is_available=False`.
- **Filtro de seletores:** Corrigido [AIModelManagerView.tsx](file:///home/spira/spirandeliempire/frontend/src/ai/AIModelManagerView.tsx) para excluir modelos `embeddings` (sem `chat`) e `retired` nos dropdowns de geração Global, Agentes, Perfis de Tarefa e Fallback.

