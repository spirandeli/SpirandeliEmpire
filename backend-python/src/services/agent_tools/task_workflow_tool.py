from decimal import Decimal
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import ApprovalQueue, Business, Task


async def create_kanban_task(
    db: AsyncSession,
    user_id: int,
    business_id: int,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    assignee: str = "agent",
    status: str = "ready",
) -> dict[str, Any]:
    """Despacha e cadastra uma nova tarefa no quadro Kanban operacional da venture.

    Args:
        business_id: ID do negócio ao qual a tarefa pertence.
        title: Título descritivo da tarefa a ser executada.
        description: Detalhes, instruções ou passos da tarefa.
        priority: Nível de prioridade ('low', 'medium', 'high', 'urgent').
        assignee: Responsável ('agent' para Jeffrey/Workers ou 'user' para humano).
        status: Coluna inicial ('backlog', 'ready', 'in_progress', 'supervision', 'done').

    Returns:
        Dicionário com a tarefa criada no Kanban.
    """
    # Valida ownership do negócio
    biz_res = await db.execute(select(Business).where(Business.id == business_id, Business.user_id == user_id))
    biz = biz_res.scalar_one_or_none()
    if not biz:
        return {"error": f"Negócio #{business_id} não encontrado ou não pertence a este usuário."}

    task = Task(
        business_id=business_id,
        user_id=user_id,
        title=title,
        description=description,
        priority=priority if priority in ("low", "medium", "high", "urgent") else "medium",
        assignee=assignee if assignee in ("agent", "user") else "agent",
        status=status if status in ("backlog", "ready", "in_progress", "supervision", "done") else "ready",
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
    """Move uma tarefa entre colunas no quadro Kanban (ex: mover para 'done' ou 'in_progress').

    Args:
        task_id: ID da tarefa a ser movida.
        new_status: Novo status ('backlog', 'ready', 'in_progress', 'supervision', 'done', 'blocked').

    Returns:
        Status atualizado da tarefa.
    """
    valid_statuses = ("backlog", "ready", "in_progress", "supervision", "done", "blocked")
    if new_status not in valid_statuses:
        return {"error": f"Status inválido. Escolha um entre: {valid_statuses}"}

    res = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = res.scalar_one_or_none()
    if not task:
        return {"error": f"Tarefa #{task_id} não encontrada."}

    old_status = task.status
    task.status = new_status
    await db.commit()

    return {
        "success": True,
        "message": f"Tarefa #{task.id} movida de '{old_status}' para '{new_status}'.",
        "task_id": task.id,
        "new_status": new_status,
    }


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

