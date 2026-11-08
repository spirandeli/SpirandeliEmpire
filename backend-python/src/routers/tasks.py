from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.dependencies import get_current_user
from src.models import Business, Task, User
from src.schemas.task import (
    TaskCreateRequest,
    TaskMoveRequest,
    TaskResponse,
    TaskUpdateRequest,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

STATUS_LABELS = {
    "backlog": "Backlog",
    "in_progress_agent": "Em Execução (IA Worker)",
    "awaiting_supervision": "Aguardando Supervisão",
    "todo_user": "A Fazer (Humano)",
    "done": "Concluído",
}

ASSIGNEE_LABELS = {
    "agent": "IA Co-Pilot",
    "user": "Operador (Você)",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _format_task(task: Task) -> dict[str, Any]:
    biz_data = None
    if task.business:
        biz_data = {"id": task.business.id, "name": task.business.name}

    return {
        "id": task.id,
        "business_id": task.business_id,
        "business": biz_data,
        "parent_id": task.parent_id,
        "title": task.title,
        "description": task.description,
        "assignee": task.assignee,
        "assignee_label": ASSIGNEE_LABELS.get(task.assignee, task.assignee.capitalize()),
        "status": task.status,
        "status_label": STATUS_LABELS.get(task.status, task.status.capitalize()),
        "priority": task.priority,
        "source": task.source,
        "position": task.position,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "agent_action": task.agent_action,
        "payload": task.payload,
        "result": task.result,
        "failure_reason": task.failure_reason,
        "attempts": task.attempts,
        "external_calendar_provider": task.external_calendar_provider,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


async def _get_user_task(task_id: int, user: User, db: AsyncSession) -> Task:
    res = await db.execute(
        select(Task).options(selectinload(Task.business)).where(
            Task.id == task_id,
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
        )
    )
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarefa não encontrada ou sem permissão de acesso.",
        )
    return t


@router.get("")
async def index(
    business_id: Optional[int] = None,
    assignee: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Task)
        .options(selectinload(Task.business))
        .where(Task.user_id == current_user.id, Task.deleted_at.is_(None))
    )
    if business_id:
        query = query.where(Task.business_id == business_id)
    if assignee:
        query = query.where(Task.assignee == assignee)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))

    query = query.order_by(Task.position.asc(), Task.id.desc())
    res = await db.execute(query)
    tasks = res.scalars().all()

    return {"data": [_format_task(t) for t in tasks]}


@router.get("/board")
async def board(
    business_id: Optional[int] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = (
        select(Task)
        .options(selectinload(Task.business))
        .where(Task.user_id == current_user.id, Task.deleted_at.is_(None))
    )
    if business_id:
        base_query = base_query.where(Task.business_id == business_id)
    if assignee:
        base_query = base_query.where(Task.assignee == assignee)
    if priority:
        base_query = base_query.where(Task.priority == priority)
    if search:
        base_query = base_query.where(Task.title.ilike(f"%{search}%"))

    # Tarefas abertas
    open_res = await db.execute(
        base_query.where(Task.status != "done").order_by(Task.position.asc(), Task.id.asc())
    )
    open_tasks = list(open_res.scalars().all())

    # Concluídas (últimas 50)
    done_res = await db.execute(
        base_query.where(Task.status == "done").order_by(Task.completed_at.desc(), Task.id.desc()).limit(50)
    )
    done_tasks = list(done_res.scalars().all())

    all_tasks = open_tasks + done_tasks

    columns = []
    for col_key, col_label in STATUS_LABELS.items():
        col_tasks = [t for t in all_tasks if t.status == col_key]
        columns.append({
            "status": col_key,
            "label": col_label,
            "count": len(col_tasks),
            "tasks": [_format_task(t) for t in col_tasks],
        })

    return {"data": columns}


@router.post("", status_code=status.HTTP_201_CREATED)
async def store(
    payload: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Valida negócio pertencente ao usuário
    biz_res = await db.execute(
        select(Business).where(Business.id == payload.business_id, Business.user_id == current_user.id)
    )
    biz = biz_res.scalar_one_or_none()
    if not biz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negócio não encontrado ou sem permissão de acesso.",
        )

    task_status = payload.status
    if not task_status:
        task_status = "backlog" if payload.assignee == "agent" else "todo_user"

    now = _utc_now()
    task = Task(
        business_id=biz.id,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        assignee=payload.assignee,
        status=task_status,
        priority=payload.priority,
        source="user",
        position=0,
        due_at=payload.due_at,
        scheduled_at=payload.scheduled_at,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    task.business = biz

    return {"data": _format_task(task)}


@router.get("/{task_id}")
async def show(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)
    return {"data": _format_task(task)}


@router.patch("/{task_id}/move")
async def move(
    task_id: int,
    payload: TaskMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)

    target_status = "done" if payload.status in ("done", "completed") else payload.status
    task.status = target_status
    if payload.position is not None:
        task.position = payload.position

    now = _utc_now()
    if target_status == "done" and not task.completed_at:
        task.completed_at = now
    elif target_status != "done":
        task.completed_at = None

    task.updated_at = now
    await db.commit()
    await db.refresh(task)

    return {"data": _format_task(task)}


@router.put("/{task_id}")
@router.patch("/{task_id}")
async def update(
    task_id: int,
    payload: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, val)

    task.updated_at = _utc_now()
    await db.commit()
    await db.refresh(task)

    return {"data": _format_task(task)}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)
    task.deleted_at = _utc_now()
    await db.commit()
    return None

