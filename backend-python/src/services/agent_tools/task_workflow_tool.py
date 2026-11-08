from decimal import Decimal
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import ApprovalQueue, Business, Task

STATUS_MAPPING = {
    "ready": "in_progress_agent",
    "in_progress": "in_progress_agent",
    "in_progress_agent": "in_progress_agent",
    "running": "in_progress_agent",
    "doing": "in_progress_agent",
    "todo": "todo_user",
    "todo_user": "todo_user",
    "supervision": "awaiting_supervision",
    "awaiting_supervision": "awaiting_supervision",
    "review": "awaiting_supervision",
    "pending_review": "awaiting_supervision",
    "done": "done",
    "completed": "done",
    "finished": "done",
    "backlog": "backlog",
}

def normalize_task_status(status: Optional[str], assignee: str = "agent") -> str:
    if not status:
        return "in_progress_agent" if assignee == "agent" else "todo_user"
    clean = status.lower().strip()
    if clean == "ready" and assignee == "user":
        return "todo_user"
    return STATUS_MAPPING.get(clean, "in_progress_agent" if assignee == "agent" else "todo_user")


async def create_kanban_task(
    db: AsyncSession,
    user_id: int,
    business_id: int,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    assignee: str = "agent",
    status: str = "in_progress_agent",
) -> dict[str, Any]:
    """Despacha e cadastra uma nova tarefa no quadro Kanban operacional da venture.

    Args:
        business_id: ID do negócio ao qual a tarefa pertence.
        title: Título descritivo da tarefa a ser executada.
        description: Detalhes, instruções ou passos da tarefa.
        priority: Nível de prioridade ('low', 'medium', 'high', 'urgent').
        assignee: Responsável ('agent' para Jeffrey/Workers ou 'user' para humano).
        status: Coluna inicial ('backlog', 'in_progress_agent', 'awaiting_supervision', 'todo_user', 'done').

    Returns:
        Dicionário com a tarefa criada no Kanban.
    """
    # Valida ownership do negócio
    biz_res = await db.execute(select(Business).where(Business.id == business_id, Business.user_id == user_id))
    biz = biz_res.scalar_one_or_none()
    if not biz:
        return {"error": f"Negócio #{business_id} não encontrado ou não pertence a este usuário."}

    norm_assignee = assignee if assignee in ("agent", "user") else "agent"
    norm_status = normalize_task_status(status, norm_assignee)

    task = Task(
        business_id=business_id,
        user_id=user_id,
        title=title,
        description=description,
        priority=priority if priority in ("low", "medium", "high", "urgent") else "medium",
        assignee=norm_assignee,
        status=norm_status,
        source="agent",
        position=0,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "message": f"Tarefa #{task.id} '{task.title}' inserida com sucesso no Kanban!",
        "task": {
            "id": task.id,
            "business_id": task.business_id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
        },
    }


async def move_kanban_task(
    db: AsyncSession,
    user_id: int,
    task_id: int,
    new_status: str,
) -> dict[str, Any]:
    """Move uma tarefa entre colunas no quadro Kanban (ex: mover para 'done' ou 'in_progress_agent').

    Args:
        task_id: ID da tarefa a ser movida.
        new_status: Novo status ('backlog', 'in_progress_agent', 'awaiting_supervision', 'todo_user', 'done').

    Returns:
        Status atualizado da tarefa.
    """
    res = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = res.scalar_one_or_none()
    if not task:
        return {"error": f"Tarefa #{task_id} não encontrada."}

    old_status = task.status
    target_status = normalize_task_status(new_status, task.assignee)
    task.status = target_status
    await db.commit()

    return {
        "success": True,
        "message": f"Tarefa #{task.id} movida de '{old_status}' para '{target_status}'.",
        "task_id": task.id,
        "new_status": target_status,
    }


async def execute_kanban_task(
    db: AsyncSession,
    user_id: int,
    task_id: int,
) -> dict[str, Any]:
    """Executa imediatamente uma tarefa do Kanban usando a IA Worker (Gemini 3.8), gerando o entregável prático (roteiro, prompts de imagem, assets ou planejamento) e enviando para a Fila de Supervisão.

    Args:
        task_id: ID da tarefa cadastrada no Kanban a ser executada.

    Returns:
        Resultado detalhado da execução da tarefa.
    """
    from src.models import User
    from src.services.task_executor_service import execute_agent_task

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return {"error": "Usuário não encontrado."}

    try:
        res = await execute_agent_task(db, task_id, user)
        return {
            "success": True,
            "message": f"Tarefa #{task_id} executada com sucesso pelo IA Worker! Entregável gerado e pronto para supervisão.",
            "deliverable": res.get("summary"),
            "status": res.get("status"),
            "assets_created": res.get("assets_created"),
        }
    except Exception as e:
        return {"error": f"Falha ao executar tarefa #{task_id} com IA Worker: {str(e)}"}


async def submit_to_approval_queue(
    db: AsyncSession,
    user_id: int,
    business_id: int,
    title: str,
    summary: str,
    payload: Optional[dict[str, Any]] = None,
    priority: str = "medium",
    task_id: Optional[int] = None,
) -> dict[str, Any]:
    """Submete um entregável, roteiro ou ação crítica para a fila de Supervisão Humana (ApprovalQueue).

    Args:
        business_id: ID do negócio relacionado.
        title: Título do card de aprovação.
        summary: Justificativa ou resumo executivo para o revisor humano.
        payload: Dados estruturados do item (roteiro, parâmetros, script).
        priority: Prioridade da revisão ('low', 'medium', 'high', 'urgent').
        task_id: ID opcional da tarefa Kanban associada.

    Returns:
        Confirmação do envio para a caixa de supervisão executiva.
    """
    item = ApprovalQueue(
        business_id=business_id,
        user_id=user_id,
        task_id=task_id,
        type="generic",
        title=title,
        summary=summary,
        payload=payload or {},
        status="pending",
        priority=priority if priority in ("low", "medium", "high", "urgent") else "medium",
        agent_confidence=Decimal("0.95"),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "success": True,
        "approval_id": item.id,
        "message": f"Item #{item.id} '{item.title}' enviado para a Supervisão Humana na Inbox!",
        "status": "pending",
    }

