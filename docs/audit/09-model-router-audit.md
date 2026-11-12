# 09 — Auditoria do AI Model Manager e Model Router

**Data:** 2026-11-12  
**Arquivos:** [model_resolver.py](file:///home/spira/spirandeliempire/backend/app/providers/model_resolver.py), [ai_settings.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/ai_settings.py), [ai_usage.py](file:///home/spira/spirandeliempire/backend/app/api/v1/endpoints/ai_usage.py)

## Hierarquia de Precedência (5 Níveis)
1. `explicit_override` (override da execução)
2. `project_config` (`ProjectModel.metadata_json["model_config"]`)
3. `agent_config` (`AgentModelConfigModel` para qualquer um dos 14 agentes oficiais)
4. `task_profile` (`TaskModelConfigModel` para os 11 perfis: `complex_planning`, `reasoning`, `coding`, `code_review`, `research`, `writing`, `summarization`, `image_analysis`, `transcription`, `fast_tasks`, `cost_efficient`)
5. `user_default` (`UserAIPreferenceModel`)

## Fallback & Consumo
- **Fallback explícito:** Desabilitado por padrão; quando `fallback_enabled=False`, erro no primário propaga sem troca oculta. Quando habilitado, percorre `fallback_chain` do usuário e registra `status="fallback_success"` + `fallback_from` (`test_dynamic_model_discovery_and_router_precedence_and_fallback`).
- **Consumo:** `AIUsageRecordModel` persiste `input_tokens`, `output_tokens`, `cached_tokens`, `total_tokens`, `duration_ms`, `provider`, `model_id`, `user_id`, `agent_id`, `project_id`, `workflow_id`, `task_id`, `status` e `error_message`.

