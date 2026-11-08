# Dicionário de Schemas e Modelos do ABVOS

## Tabela: `businesses`
Representa uma venture digital independente dentro do sistema.
- `id` (BIGINT UNSIGNED, PK): Identificador único.
- `user_id` (BIGINT UNSIGNED, FK): Dono do negócio.
- `name` (VARCHAR 255): Nome comercial da venture.
- `slug` (VARCHAR 255): Slug identificador URL.
- `type` / `archetype` (VARCHAR 48): Tipo de negócio (`affiliate_tiktok`, `dropshipping`, `saas`, `custom`).
- `north_star_metric` (VARCHAR 48): Métrica primária (`commission_volume`, `mrr`, `net_profit`).
- `target_kpi_value` (DECIMAL 12,2): Alvo numérico de faturamento ou volume.
- `status` (VARCHAR 32): `draft`, `active`, `paused`, `archived`.
- `canvas`, `brand_rules`, `goals`, `metrics` (JSON): Configuração estratégica detalhada.

## Tabela: `tasks`
Gerenciamento de tarefas do Kanban operacional.
- `id` (BIGINT UNSIGNED, PK).
- `business_id` (BIGINT UNSIGNED, FK).
- `user_id` (BIGINT UNSIGNED, FK).
- `title` (VARCHAR 255), `description` (TEXT).
- `assignee` (VARCHAR 16): `agent` (Jeffrey / Worker) ou `user` (humano).
- `status` (VARCHAR 32): `backlog`, `ready`, `in_progress`, `supervision`, `done`, `blocked`.
- `priority` (VARCHAR 16): `low`, `medium`, `high`, `urgent`.

## Tabela: `approval_queues`
Fila Human-in-the-Loop para revisão de entregáveis e ações sensíveis.
- `id` (BIGINT UNSIGNED, PK).
- `business_id` (BIGINT UNSIGNED, FK).
- `task_id` (BIGINT UNSIGNED, FK, opcional).
- `type` (VARCHAR 48): `tiktok_script`, `growth_experiment`, `vps_action`, `generic`.
- `title` (VARCHAR 255), `summary` (TEXT), `payload` (JSON).
- `status` (VARCHAR 32): `pending`, `approved`, `rejected`, `revision_requested`.

## Tabela: `agent_memories`
Memória de longo prazo do Jeffrey por usuário e venture.
- `category` (VARCHAR 48): `fact`, `preference`, `strategy`, `guideline`, `decision`.
- `key` (VARCHAR 128): Identificador único semântico.
- `content` (TEXT): Conteúdo textual da memória.
- `importance` (SMALLINT): Escala de 1 a 10.

