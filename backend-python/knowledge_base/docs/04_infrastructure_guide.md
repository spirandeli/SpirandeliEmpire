# Guia de Infraestrutura, Segurança e Docker

## Contêineres Padrão do Sistema
- `abvos-app-py`: Backend FastAPI (Python 3.12, Uvicorn, SQLAlchemy).
- `abvos-node`: Servidor de desenvolvimento Vite / Vue 3 SPA.
- `abvos-web`: Nginx 1.27 atuando como Gateway reverso na porta 8080 (ou configurada via WEB_PORT).
- `abvos-db`: Instância MySQL 8.0 persistida no volume `db_data`.
- `abvos-redis`: Instância Redis 7 persistida no volume `redis_data`.
- `abvos-mailpit`: Servidor de captura de e-mails em ambiente de desenvolvimento.

## Políticas de Segurança do Agente
1. **Docker Socket**: O socket `/var/run/docker.sock` é montado exclusivamente em modo de leitura (`:ro`).
2. **Auditoria de Ações**: Todas as chamadas de ferramentas operacionais geram entradas estruturadas na tabela `agent_logs`.
3. **Ações Críticas**: Nenhuma ação que reinicie serviços, altere configurações de rede ou modifique banco de produção deve ser executada sem criar um card pendente em `approval_queues`.
4. **Isolamento de Tenants**: Todas as consultas e operações do banco de dados são obrigatoriamente filtradas por `user_id` e validadas por autenticação JWT Bearer.

