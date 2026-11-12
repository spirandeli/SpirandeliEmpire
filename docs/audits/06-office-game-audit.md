# 06 — Auditoria do Escritório Virtual 2D (Phaser 3)

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 06 — Motor Phaser 3, Composição do Mapa Pixel-Art, os 14 Agentes, Integração Backend/WebSocket, Navegação/Pathfinding, Performance e Validação Visual no Navegador.

---

## 1. Resumo Executivo

O Escritório Virtual 2D ([OfficeScene.ts](file:///home/spira/spirandeliempire/frontend/src/office/OfficeScene.ts) e [VirtualOffice.tsx](file:///home/spira/spirandeliempire/frontend/src/office/VirtualOffice.tsx)) é um cenário pixel-art contínuo e navegável construído em **Phaser 3.87.0** (`pixelArt: true`, `roundPixels: true`, `Phaser.Scale.RESIZE`), com **tilemap 58×38** (`1856×1216 px`), **8 salas conectadas por corredores e portas**, **159 móveis/props customizados**, **303 segmentos de parede** e **14 spritesheets animados** (`32×48 px`, 13 linhas de animação por personagem).

Não se trata de cartões estáticos nem de simulação por timers aleatórios: os estados visuais respondem a eventos reais do backend via WebSocket (`/api/v1/events`) e carregam dados reais do banco.

---

## 2. Problemas Encontrados e Correções Aplicadas

1. **Ícone de trabalho (`status_coding`) invisível para estado `Working`:**
   - **Problema:** `VirtualOffice.tsx` enviava `updateAgentVisualState(agent_id, 'Working')` ao receber `AgentStarted`/`TaskAssigned`, porém `OfficeScene.ts` (linha 443) exibia o ícone apenas quando `s === 'coding'`.
   - **Correção:** Atualizado [OfficeScene.ts](file:///home/spira/spirandeliempire/frontend/src/office/OfficeScene.ts#L441-L443) para exibir `status_coding` em `coding`, `working` e `creating`.
2. **Evento `AgentFailed` não refletido no escritório:**
   - **Problema:** O listener WebSocket de `VirtualOffice.tsx` não tratava `AgentFailed`.
   - **Correção:** Adicionado tratamento de `AgentFailed` -> `'error'` (exibe `status_alert`) em [VirtualOffice.tsx](file:///home/spira/spirandeliempire/frontend/src/office/VirtualOffice.tsx#L125-L127).
3. **Drawer do agente exibia `assigned_tasks` vazio:**
   - **Problema:** `AgentModel.assigned_tasks` não recebia as tarefas criadas em `TaskModel`.
   - **Correção:** Ao clicar em um agente, `VirtualOffice.tsx` agora consulta em paralelo `api.getAgent(agentId)` e `api.getTasks({ agent_id: agentId })`, exibindo as tarefas reais persistidas no PostgreSQL.

---

## 3. Verificação Técnica por Área

| Área | Evidência Observada | Status |
| :--- | :--- | :---: |
| **Phaser & Assets** | Tilemap `58×38`, tileset `office_floors.png`, 303 paredes, 159 props, 5 tapetes, 14 spritesheets `32×48` | **PASS** |
| **14 Agentes** | Todos os 14 agentes presentes sem duplicação (`jeffrey`, `fonseca`, `balsini`, `noe`, `ford`, `jarvis`, `script_agent`, `news_agent`, `murphy`, `voice_agent`, `subtitle_agent`, `clipador_agent`, `designer_agent`, `video_agent`) | **PASS** |
| **Navegação & Pathfinding** | Algoritmo A* (`findPathAStar`) sobre `collisionGrid` com 4 direções e animação `walk_*` + depth sorting (`setDepth(y)`) | **PASS** |
| **Câmera, Zoom & Mobile** | Pan por arraste, zoom por scroll/botões, pinch-to-zoom multi-touch (`addPointer(1)`), atalhos de câmera para as 8 salas e `hasOverflow: false` em `390×844` | **PASS** |
| **Integração Backend** | `api.getAgents()`, `api.getAgent(id)`, `api.getTasks()`, `api.startWorkflow()`, WebSocket `/api/v1/events` | **PASS** |

*Observação visual menor:* Em zoom distante (`Tudo` em `1920×1080`), as `nameTag` dos agentes sentados de costas (`back`) ficam parcialmente sobrepostas à base da cadeira; ao focar na sala ou no mobile, a leitura fica nítida.

---

## 4. Evidências Visuais Playwright (`docs/audits/screenshots/office/`)

Executado `pw_office_audit.mjs` contra `http://localhost:8086` (`canvas: 1654×968`, `mobile 390×844 hasOverflow: false`):
- `01-office-full.png` — Escritório completo com 8 salas e 14 agentes
- `02-room-dev.png` — Development Wing (`Fonseca`, `Balsini`, `Noé`, `Ford`)
- `03-room-ceo.png` — CEO Office (`Jeffrey`)
- `04-room-infra.png` — Infrastructure & Servers (`Jarvis`)
- `05-room-qa.png` — QA Quality Gate (`Murphy`)
- `06-room-content.png` — Content Studio (`Script Agent`, `News Agent`)
- `07-room-audiovisual.png` — Audiovisual Studio (`Voice`, `Subtitle`, `Clipador`, `Designer`, `Video`)
- `08-agent-selected.png` — Agente selecionado com anel de seleção e drawer lateral
- `09-characters-moving-meeting.png` — Agentes caminhando via A* para Reunião Geral
- `10-office-mobile-390x844.png` — Visão Mobile `390×844` sem overflow horizontal

