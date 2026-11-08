import inspect
import logging
from typing import Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agent_tools.vps_tool import get_vps_telemetry
from src.services.agent_tools.docker_tool import list_docker_containers, get_docker_container_logs
from src.services.agent_tools.venture_tool import list_user_ventures, create_business_venture
from src.services.agent_tools.task_workflow_tool import create_kanban_task, move_kanban_task, submit_to_approval_queue
from src.services.agent_tools.knowledge_tool import search_knowledge_tool

logger = logging.getLogger("abvos.agent_tools")

# Metadados amigáveis para UI e logs
TOOL_METADATA = {
    "get_vps_telemetry": {
        "title": "Telemetria da VPS",
        "category": "infra",
        "description": "Lendo métricas de hardware da VPS (CPU, RAM, Disco)...",
    },
    "list_docker_containers": {
        "title": "Status dos Contêineres Docker",
        "category": "infra",
        "description": "Consultando contêineres ativos no Docker Engine...",
    },
    "get_docker_container_logs": {
        "title": "Logs do Contêiner",
        "category": "infra",
        "description": "Recuperando logs de erro e diagnóstico...",
    },
    "list_user_ventures": {
        "title": "Listar Negócios / Ventures",
        "category": "business",
        "description": "Consultando negócios ativos no portfólio...",
    },
    "create_business_venture": {
        "title": "Criar Nova Venture",
        "category": "business",
        "description": "Registrando e ativando nova venture no banco...",
    },
    "create_kanban_task": {
        "title": "Criar Tarefa no Kanban",
        "category": "task",
        "description": "Despachando nova tarefa operacional...",
    },
    "move_kanban_task": {
        "title": "Atualizar Status de Tarefa",
        "category": "task",
        "description": "Movimentando tarefa no fluxo de trabalho...",
    },
    "submit_to_approval_queue": {
        "title": "Submeter à Supervisão Humana",
        "category": "governance",
        "description": "Encaminhando entregável para a Inbox de aprovação...",
    },
    "search_knowledge_tool": {
        "title": "Busca na Base de Conhecimento",
        "category": "rag",
        "description": "Consultando SOPs e regras no banco vetorial...",
    },
}


# Mapeamento interno das funções
TOOL_DISPATCH_TABLE: dict[str, Callable[..., Any]] = {
    "get_vps_telemetry": get_vps_telemetry,
    "list_docker_containers": list_docker_containers,
    "get_docker_container_logs": get_docker_container_logs,
    "list_user_ventures": list_user_ventures,
    "create_business_venture": create_business_venture,
    "create_kanban_task": create_kanban_task,
    "move_kanban_task": move_kanban_task,
    "submit_to_approval_queue": submit_to_approval_queue,
    "search_knowledge_tool": search_knowledge_tool,
}


def get_gemini_tools_declarations() -> list[dict[str, Any]]:
    """Gera schemas de declaração de funções no formato aceito pelo Google GenAI."""
    declarations = [
        {
            "name": "get_vps_telemetry",
            "description": "Obtém telemetria em tempo real do host/VPS: CPU, RAM, disco, load average e uptime.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "list_docker_containers",
            "description": "Lista o status, imagem e saúde dos contêineres Docker do ABVOS (app-py, db, redis, web, node).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "all_containers": {
                        "type": "BOOLEAN",
                        "description": "Se True, lista contêineres parados também.",
                    }
                },
            },
        },
        {
            "name": "get_docker_container_logs",
            "description": "Recupera os últimos logs (stdout/stderr) de um contêiner específico (ex: 'abvos-app-py', 'abvos-db').",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "container_name": {
                        "type": "STRING",
                        "description": "Nome do contêiner (ex: 'abvos-app-py', 'abvos-web').",
                    },
                    "lines": {
                        "type": "INTEGER",
                        "description": "Quantidade de linhas a recuperar (default 50).",
                    },
                },
                "required": ["container_name"],
            },
        },
        {
            "name": "list_user_ventures",
            "description": "Lista todos os negócios (ventures) do usuário logado com métricas, status e arquétipo.",
            "parameters": {
                "type": "OBJECT",
                "properties": {},
            },
        },
        {
            "name": "create_business_venture",
            "description": "Cria um novo negócio / empreendimento digital no banco de dados.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "Nome comercial da venture."},
                    "archetype": {
                        "type": "STRING",
                        "description": "Arquétipo ('affiliate_tiktok', 'dropshipping', 'saas', 'custom').",
                    },
                    "niche": {"type": "STRING", "description": "Nicho de atuação."},
                    "description": {"type": "STRING", "description": "Resumo do negócio ou tese de validação."},
                    "target_kpi_value": {"type": "NUMBER", "description": "Meta numérica de KPI financeiro."},
                },
                "required": ["name"],
            },
        },
        {
            "name": "create_kanban_task",
            "description": "Cria e despacha uma nova tarefa no quadro Kanban da venture.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "business_id": {"type": "INTEGER", "description": "ID do negócio associado."},
                    "title": {"type": "STRING", "description": "Título da tarefa."},
                    "description": {"type": "STRING", "description": "Instruções ou escopo detalhado."},
                    "priority": {"type": "STRING", "description": "Prioridade: low, medium, high, urgent."},
                    "assignee": {"type": "STRING", "description": "Responsável: 'agent' ou 'user'."},
                    "status": {"type": "STRING", "description": "Coluna inicial: 'backlog', 'ready', 'in_progress'."},
                },
                "required": ["business_id", "title"],
            },
        },
        {
            "name": "move_kanban_task",
            "description": "Atualiza a coluna/status de uma tarefa existente no Kanban.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "task_id": {"type": "INTEGER", "description": "ID da tarefa."},
                    "new_status": {
                        "type": "STRING",
                        "description": "Novo status ('backlog', 'ready', 'in_progress', 'supervision', 'done', 'blocked').",
                    },
                },
                "required": ["task_id", "new_status"],
            },
        },
        {
            "name": "submit_to_approval_queue",
            "description": "Submete um roteiro, entregável ou alteração para a caixa de Supervisão Humana (ApprovalQueue).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "business_id": {"type": "INTEGER", "description": "ID do negócio associado."},
                    "title": {"type": "STRING", "description": "Título do entregável para revisão."},
                    "summary": {"type": "STRING", "description": "Resumo executivo do que deve ser aprovado."},
                    "payload": {"type": "OBJECT", "description": "Dados estruturados do entregável."},
                    "priority": {"type": "STRING", "description": "Prioridade da revisão."},
                    "task_id": {"type": "INTEGER", "description": "ID opcional da tarefa associada."},
                },
                "required": ["business_id", "title", "summary"],
            },
        },
        {
            "name": "search_knowledge_tool",
            "description": "Busca semântica na base de conhecimento oficial do ABVOS (modelos de negócio, regras de comissão, schemas, infraestrutura).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Pergunta ou termos de busca na base."},
                    "limit": {"type": "INTEGER", "description": "Quantidade de resultados (default 3)."},
                },
                "required": ["query"],
            },
        },
    ]
    return declarations


async def execute_agent_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Executa a ferramenta chamada pelo Gemini com injeção segura de dependências."""
    func = TOOL_DISPATCH_TABLE.get(tool_name)
    if not func:
        return {"error": f"Ferramenta desconhecida: '{tool_name}'."}

    sig = inspect.signature(func)
    kwargs = dict(tool_args or {})

    # Injeta parâmetros de contexto se a função solicitar
    if "db" in sig.parameters:
        kwargs["db"] = db
    if "user_id" in sig.parameters:
        kwargs["user_id"] = user_id

    try:
        if inspect.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = func(**kwargs)
        return result
    except Exception as e:
        logger.exception(f"Erro ao executar tool {tool_name}")
        return {"error": f"Falha na execução de {tool_name}: {str(e)}"}

