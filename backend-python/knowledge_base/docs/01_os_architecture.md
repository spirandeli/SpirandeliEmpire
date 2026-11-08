# SpirandeliEmpire OS (ABVOS) - Arquitetura de Produção

## Visão Geral
O Autonomous Business Venture OS (ABVOS) é a plataforma executiva criada para conceber, lançar, validar e escalar múltiplos modelos de negócio digitais simultâneos (Ventures) de forma altamente automatizada e supervisionada por inteligência artificial.

## Stack Tecnológica
- **Backend**: FastAPI (Python 3.12) assíncrono com SQLAlchemy 2.0 ORM (`aiomysql`), Pydantic v2 e Pydantic-Settings.
- **Orquestrador de IA**: Jeffrey (COO Virtual) operando sob o modelo Gemini 3.8 Flash (`google-genai` SDK) com ciclo ReAct e fallback em cascata.
- **Banco de Dados**: MySQL 8.0 (`abvos-db`) com foreign keys em cascata e índices compostos.
- **Cache & Filas**: Redis 7 Alpine (`abvos-redis`) para locks distribuídos, cache e filas de background workers (ARQ).
- **Frontend SPA**: Vue 3 (Composition API), Vite, Tailwind CSS, Pinia e SweetAlert2/Heroicons.
- **Reverse Proxy**: Nginx 1.27 Alpine (`abvos-web`) roteando `/api` para o backend e `/` para a SPA.

## Fluxo Operacional
1. O usuário e o Jeffrey interagem via Chat Drawer ou Dashboard Cockpit.
2. O Jeffrey opera como Diretor de Operações (COO), utilizando Function Calling seguro para auditar a VPS, inspecionar contêineres Docker, consultar e criar negócios (`businesses`), movimentar tarefas no Kanban (`tasks`) e despachar itens para a fila de aprovação (`approval_queues`).
3. O princípio Human-in-the-Loop garante que nenhuma ação destrutiva de infraestrutura ocorra sem aprovação humana expressa.

