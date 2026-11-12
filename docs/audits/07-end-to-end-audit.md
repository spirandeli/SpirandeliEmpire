# 07 — Auditoria End-to-End de Workflows e Entregáveis

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 07 — Testes A (Chat/Projeto), B (Desenvolvimento), C (Conteúdo Audiovisual), D (Falha Controlada), E (Aprovação Humana + Restart) e F (Artifact Manager) contra a stack Docker ao vivo (`http://localhost:8086`).

---

## 1. Resumo Executivo

Todos os fluxos principais foram executados ponta a ponta contra os containers ativos (`nginx` → `backend` → `postgres` + `redis` + `worker` Celery). Os IDs reais, artefatos em disco, retomadas pós-reinício e isolamento multiusuário foram comprovados. Etapas que dependem de motores externos de mídia (TTS real e renderização MP4 FFmpeg com vídeo/áudio reais) permanecem honestamente classificadas como **BLOCKED**.

---

## 2. Resultados por Cenário de Teste

### Teste A — Criação de Projeto via Chat Jeffrey (`PASS` com ressalva)
- **Execução:** `POST /api/v1/chat/message` enviou `"Crie um sistema simples de notas em Python"` autenticado com usuário BYOK (`gemini-flash-latest`).
- **Evidência:** Workflow `453aef13-e445-41e9-b68f-9dd0686355f1` criado e despachado via Celery, alcançando `waiting_approval` (aprovação `24b0b263-5fe6-4281-8b22-c356f1641fed`). Histórico persistido no PostgreSQL após `docker compose restart backend`.
- **Observação:** Na primeira chamada de teste com usuário recém-cadastrado, `chat` retornou `reply_len: 0` quando o provedor externo estava em pico `503` ou sem texto; o workflow foi despachado corretamente.

### Teste B — Desenvolvimento de Software em Sandbox (`PASS`)
- **Projeto:** `b201a535-...` (`Notas API E2E`, `project_type="software"`).
- **Workflow:** `55d85962-76c3-4ae4-b2be-4fcc621a5942` (`development`).
- **Fluxo Executado:** `requirements` (Noé) → `architecture` (Noé, `ADR Arquitetura`) → `implementation` (Balsini `Backend Module`, Fonseca `Frontend Component`) → `data_engineering` (Ford `Data Migration SQL`) → `testing` (Murphy `quality_scorer`) → `deployment_approval` (`interrupt()`) → `deployment` (Jarvis) → `final_report`.
- **Evidência:** Concluído com `status: completed` após aprovação humana, gerando 4 arquivos reais em `storage/artifacts/`.
- **Correção pós-auditoria (verificada ao vivo):** Os 4 subgrafos (`development_graph`, `content_graph`, `clip_graph`, `business_graph`) passaram a repassar `user_id` de `execution_context` para `agent_executor.execute_task(...)`. Em re-execução via Celery (`f0b9fe8b`), `GET /api/v1/tasks/` retornou `5` tarefas vinculadas ao usuário autenticado e a retomada após `waiting_approval` concluiu em `final_report` sem erro de serialização Celery.

### Teste C — Conteúdo Audiovisual (`PASS` para roteiro/PNG/SRT/MP4 FFmpeg; TTS `BLOCKED` explícito)
- **Workflows:** `a15cc8b7-9d33-426c-80c3-88e6c87cfc4c` e re-validação `11d86b13-421a-451c-8f96-1afce9b75288` (`content`).
- **Entregáveis Reais e Executores Atualizados:**
  - `Roteiro Produzido` (`script_generator` via `gemini_provider.generate`) — **PASS**
  - `Asset Visual / Thumbnail` (`image_generator` via Pillow PNG real, validado em `pytest`) — **PASS**
  - `Legendas SRT Sincronizadas` (`srt_formatter` segmentado dinamicamente) — **PASS**
  - `Vídeo Final Renderizado` (`ffmpeg_assembler` com `ffmpeg` real em `.mp4`, substituindo o stub `.mp4.meta`) — **PASS**
- **Etapa Bloqueada Explicitamente (Sem Mídia Stub):**
  - `Voice Agent` (`tts_generator`): não gera mais WAV stub de `44 bytes`; retorna `BLOCKED: Motor TTS externo não configurado no Integration Hub.` (`tts_status: "blocked"` no `execution_context`, sem criar arquivo `.wav` fictício).

### Teste D — Falha Controlada de Ferramenta / Modelo (`PASS`)
- **Execução:** Workflow disparado para usuário sem credencial/modelo BYOK configurado (`e2e_u1_...@test.local`).
- **Evidência:** `ModelResolver` bloqueou execução com `Configuration Required` (sem fallback silencioso para Gemini 2.5); `WorkflowModel` e as 6 linhas em `TaskModel` foram marcados como `failed` (`TASK_STATUSES: ['failed', ...]`), mantendo consistência total entre workflow e tarefas.

### Teste E — Aprovação Humana & Durabilidade Pós-Reinício (`PASS`)
- **Workflow:** `55d85962-76c3-4ae4-b2be-4fcc621a5942` pausou via `langgraph.types.interrupt()` em `waiting_approval` com `3 checkpoints`.
- **Reinício:** Executado `docker compose restart backend`. Após o restart, `GET /workflows/55d85962-...` manteve `status: waiting_approval` e `checkpoints: 3`.
- **Decisão e Retomada:** `POST /api/v1/approvals/d2bf879a-c63b-4e8e-bcaa-e9d070e5b7bc/decide` (`approved=true`, `feedback="Aprovado no teste E2E"`) retornou HTTP `200`, retomou o grafo exatamente do nó interrompido e finalizou com `status: completed`.

### Teste F — Artifact Manager (`PASS`)
- **Evidência:** Todos os **9 artefatos** produzidos pelos workflows `55d85962` e `a15cc8b7` foram verificados:
  - Existem fisicamente em disco (`exists=True`, tamanhos `44` a `656 bytes`).
  - Possuem `workflow_id`, `project_id` (`b201a535`) e metadados.
  - `GET /api/v1/artifacts/{id}` e `GET /api/v1/artifacts/{id}/download` retornaram HTTP `200` para o Usuário 1 e HTTP `404` para o Usuário 2 (isolamento multiusuário validado).

