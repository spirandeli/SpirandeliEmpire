# 10 — Auditoria de LangGraph, Agentes, Tools e Workers

**Data:** 2026-11-12

- **Busca por referências fixas Gemini 2.5:** `grep -rn "gemini-2\.5\|ChatGoogleGenerativeAI\|genai\.Client" backend/app/` retornou apenas `gemini_provider.py` (usado para compatibilidade legada / testes sem `user_id`, com mapeamento legado e sem dependência obrigatória nos grafos).
- **14 Agentes Oficiais:** Todos os 14 agentes (`jeffrey`, `fonseca`, `balsini`, `jarvis`, `noe`, `ford`, `murphy`, `script_agent`, `voice_agent`, `subtitle_agent`, `clipador_agent`, `news_agent`, `designer_agent`, `video_agent`) executam via `AgentExecutor` e `ModelRouter` quando `user_id` está presente.
- **Propagação de `user_id` e Estado Seguro:** Os 5 grafos (`jeffrey_supervisor_graph`, `development_graph`, `content_graph`, `clip_graph`, `business_graph`) propagam `user_id` via `execution_context` sem armazenar API keys no estado LangGraph ou nos checkpoints.
- **Function Calling / Tools:** Corrigido [executor.py](file:///home/spira/spirandeliempire/backend/app/agents/executor.py) para injetar `content_text` também em `script_generator`, e atualizado `_script_generator_executor` em [tools/registry.py](file:///home/spira/spirandeliempire/backend/app/tools/registry.py) para rotear via `model_router` quando `user_id` é informado.
- **Celery Worker ([celery_app.py](file:///home/spira/spirandeliempire/backend/app/workers/celery_app.py)):** Corrigida serialização JSON de objetos `Interrupt` com `json.loads(json.dumps(res, default=str))`; retestado ao vivo com `development` (`waiting_approval` → `resume` → `completed`).

