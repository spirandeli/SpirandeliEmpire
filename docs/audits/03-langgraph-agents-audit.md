# 03 — Auditoria LangGraph e dos 14 Agentes

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 03 — Jeffrey, os 14 Agentes Oficiais, LangGraph, Checkpoints/Durabilidade, Delegação, Human-in-the-Loop e Economia de Recursos.

---

## 1. Resumo Executivo

A auditoria inicial revelou que os 5 grafos LangGraph usavam `InMemorySaver()`, não utilizavam `interrupt()` para Human-in-the-Loop e não invocavam o LLM nos nós dos 13 especialistas. Além disso, o `GeminiProvider` não lia a chave salva no Integration Hub (PostgreSQL) e usava nomes de modelos legados (`gemini-2.5-flash` / `gemini-2.5-pro`) que retornavam `404 NOT_FOUND` na API Gemini.

Todos os problemas estruturais foram corrigidos, com implementação de checkpointer durável em disco, motor unificado de execução para os 14 agentes (`AgentExecutor`), delegação paralela controlada por dependências, substituição automática de agente em caso de falha e interrupção/retomada real via `langgraph.types.interrupt` e `Command(resume=...)`.

---

## 2. Os 14 Agentes Oficiais — Validação Individual

Todos os **14 agentes** em [registry.py](file:///home/spira/spirandeliempire/backend/app/agents/registry.py) foram verificados sem duplicações e executados individualmente via `agent_executor.execute_task(...)` ([executor.py](file:///home/spira/spirandeliempire/backend/app/agents/executor.py)) utilizando `test-provider` injetado (`gemini_provider.set_test_handler`):

| # | ID | Nome | Departamento | Modelo | Execução Individual | Persistência DB (`TaskModel`/`AgentModel`) |
| :-: | :--- | :--- | :--- | :--- | :---: | :---: |
| 1 | `jeffrey` | Jeffrey | Executive | `gemini-3.1-pro-preview` | **PASS** (test-provider) | **PASS** |
| 2 | `fonseca` | Fonseca | Development | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 3 | `balsini` | Balsini | Development | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 4 | `jarvis` | Jarvis | Infrastructure | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 5 | `noe` | Noé | Development | `gemini-3.1-pro-preview` | **PASS** (test-provider) | **PASS** |
| 6 | `ford` | Ford | Development | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 7 | `murphy` | Murphy | QA | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 8 | `script_agent` | Script Agent | Content | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 9 | `news_agent` | News Agent | Content | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 10 | `voice_agent` | Voice Agent | Audiovisual | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 11 | `subtitle_agent` | Subtitle Agent | Audiovisual | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 12 | `clipador_agent` | Clipador Agent | Audiovisual | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 13 | `designer_agent` | Designer Agent | Audiovisual | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |
| 14 | `video_agent` | Video Agent | Audiovisual | `gemini-3.8-flash` | **PASS** (test-provider) | **PASS** |

> [!NOTE]
> Os testes unitários/integração acima usaram `test-provider` (`gemini_provider.set_test_handler`) para isolamento determinístico, sem mascarar resultados como chamadas reais à API Gemini. Em testes contra o PostgreSQL com chave real do Integration Hub, modelos `gemini-2.5-*` retornavam `404 NOT_FOUND` e foram atualizados para `gemini-3.8-flash` e `gemini-3.1-pro-preview`.

---

## 3. Correções Arquiteturais Implementadas

1. **Checkpointer Durável ([persistent_saver.py](file:///home/spira/spirandeliempire/backend/app/orchestrator/checkpoints/persistent_saver.py)):**
   - Substituído `InMemorySaver()` por `PersistentCheckpointSaver`, persistindo `storage`, `writes` e `blobs` por `thread_id` de forma atômica em `storage/checkpoints/{thread_id}.lgckpt.pkl`.
2. **Motor Unificado dos 14 Agentes ([executor.py](file:///home/spira/spirandeliempire/backend/app/agents/executor.py)):**
   - Atualiza `AgentModel.operational_state`, `metrics` e `history` (limitado às últimas 20 entradas).
   - Cria/atualiza `TaskModel` em sincronia com o workflow (falhas no workflow marcam tarefas pendentes/em andamento como `failed`/`cancelled`, nunca `completed`).
   - Carrega apenas memória escopada (`MemoryModel`, máximo 5 entradas) e resumos compactos das dependências (`<= 500 chars`).
3. **Human-in-the-Loop Real (`interrupt` + `Command(resume=...)`):**
   - Implementado `langgraph.types.interrupt()` em `jeffrey_supervisor_graph.py`, `development_graph.py`, `clip_graph.py` e `business_graph.py`.
   - `WorkflowManager` ([manager.py](file:///home/spira/spirandeliempire/backend/app/orchestrator/workflows/manager.py)) inspeciona `graph.aget_state(config)`, cria `ApprovalModel` no banco, sanitiza objetos `Interrupt` antes de gravar JSON e retoma exatamente do nó interrompido via `Command(resume=...)`.
4. **Delegação Paralela, Substituição e Limites de Recursos:**
   - `execute_plan_node` em [jeffrey_supervisor_graph.py](file:///home/spira/spirandeliempire/backend/app/orchestrator/graphs/jeffrey_supervisor_graph.py) executa ondas paralelas respeitando `dependencies` e `asyncio.Semaphore(3)`.
   - Falhas de especialistas acionam substituição automática (`BACKUP_AGENT_MAP`) ou replanejamento limitado a `MAX_REPLAN_ITERATIONS = 3`.
   - `GeminiProvider` ([gemini_provider.py](file:///home/spira/spirandeliempire/backend/app/providers/gemini_provider.py)) agora lê a chave encriptada do `IntegrationModel` no banco, limita prompt a `24.000` chars e histórico a `6` turnos.
   - Corrigida permissão de `file_writer` em [tools/registry.py](file:///home/spira/spirandeliempire/backend/app/tools/registry.py) para `clipador_agent`, `designer_agent`, `video_agent` e `murphy`.

---

## 4. Evidências de Testes Executados

Suíte executada em [test_langgraph_and_14_agents.py](file:///home/spira/spirandeliempire/backend/tests/test_langgraph_and_14_agents.py) + suíte completa (`cd backend && uv run pytest -v`):
- `test_all_14_agents_execute_individually`: **PASS**
- `test_parallel_delegation_and_dependency_sharing`: **PASS**
- `test_agent_failure_and_substitution`: **PASS** (`balsini` falhou simuladamente → substituído por `noe` → `completed`)
- `test_durability_interrupt_restart_and_human_approval`: **PASS** (`waiting_approval` → novo `PersistentCheckpointSaver` recupera checkpoint do disco → `decide_approval(True)` → `completed`)
- `test_human_in_the_loop_rejection_and_rbac`: **PASS** (`decide_approval(False)` → `rejected`)
- **Total (SQLite):** `23 passed in 4.95s`

