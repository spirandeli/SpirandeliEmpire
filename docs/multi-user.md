# Arquitetura Multiusuário e Isolamento (SpirandeliEmpire OS 3.2)

## Isolamento Estrito por `user_id`
Cada usuário possui dados completamente isolados no backend:
- Credenciais de provedores de IA (`ai_provider_credentials`)
- Catálogos de modelos sincronizados (`ai_models`)
- Preferências globais, configurações dos 14 agentes e perfis de tarefa (`user_ai_preferences`, `agent_model_configs`, `task_model_configs`)
- Projetos, Tarefas, Workflows, Artefatos, Aprovações, Memórias e Mensagens de Chat (`user_id` obrigatório nas consultas de serviço e endpoints)
- Registros de consumo (`ai_usage_records`)

## Papéis (RBAC)
- **`ADMIN`** (legado `owner`): Gerencia usuários (`GET/PATCH /api/v1/users/admin/users`), políticas de cadastro (`GET/PATCH /api/v1/users/admin/policies`) e convites (`POST /api/v1/users/admin/invites`). **Nunca visualiza o valor integral de API keys de outros usuários.**
- **`USER`**: Opera projetos, workflows, chat com Jeffrey e suas próprias credenciais/modelos BYOK.
- **`VIEWER`**: Acesso somente leitura aos seus próprios recursos.

