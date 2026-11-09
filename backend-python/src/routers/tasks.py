import logging
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.database import get_db, AsyncSessionLocal
from src.dependencies import get_current_user
from src.models import Business, Task, User
from src.schemas.task import (
    TaskCreateRequest,
    TaskMoveRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from src.services.task_executor_service import execute_agent_task
from src.routers.media import scan_task_media_dir
from src.routers.storage_viewer import delete_task_storage_dirs

logger = logging.getLogger("abvos.routers.tasks")


async def _bg_execute_task(task_id: int, user: User):
    """
    Executa a tarefa em background quando arrastada para in_progress_agent.
    """
    try:
        async with AsyncSessionLocal() as session:
            await execute_agent_task(session, task_id, user)
    except Exception as e:
        logger.error(f"Erro ao executar tarefa #{task_id} em background: {e}")

router = APIRouter(prefix="/tasks", tags=["Tasks"])

STATUS_LABELS = {
    "backlog": "Backlog",
    "in_progress_agent": "Em Execução (IA Worker)",
    "awaiting_supervision": "Aguardando Supervisão",
    "todo_user": "A Fazer (Humano)",
    "done": "Concluído",
}

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
        return "backlog" if assignee == "agent" else "todo_user"
    clean = status.lower().strip()
    if clean == "ready" and assignee == "user":
        return "todo_user"
    return STATUS_MAPPING.get(clean, "in_progress_agent" if assignee == "agent" else "todo_user")

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

    norm_status = normalize_task_status(task.status, task.assignee)

    return {
        "id": task.id,
        "business_id": task.business_id,
        "business": biz_data,
        "parent_id": task.parent_id,
        "title": task.title,
        "description": task.description,
        "assignee": task.assignee,
        "assignee_label": ASSIGNEE_LABELS.get(task.assignee, task.assignee.capitalize()),
        "status": norm_status,
        "status_label": STATUS_LABELS.get(norm_status, norm_status.capitalize()),
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
        "status_log": getattr(task, "status_log", None),
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

    # Tarefas abertas (qualquer status que não normalize para 'done')
    raw_open_res = await db.execute(base_query.order_by(Task.position.asc(), Task.id.asc()))
    all_raw_tasks = list(raw_open_res.scalars().all())

    open_tasks = [t for t in all_raw_tasks if normalize_task_status(t.status, t.assignee) != "done"]
    done_tasks = [t for t in all_raw_tasks if normalize_task_status(t.status, t.assignee) == "done"][:50]

    all_tasks = open_tasks + done_tasks

    columns = []
    for col_key, col_label in STATUS_LABELS.items():
        col_tasks = [t for t in all_tasks if normalize_task_status(t.status, t.assignee) == col_key]
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
    background_tasks: BackgroundTasks,
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

    task_status = normalize_task_status(payload.status, payload.assignee)

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

    if task_status == "in_progress_agent" and task.assignee == "agent":
        background_tasks.add_task(_bg_execute_task, task.id, current_user)

    return {"data": _format_task(task)}


@router.get("/{task_id}")
async def show(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)
    return {"data": _format_task(task)}


@router.get("/{task_id}/media")
async def get_task_media(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna a lista e manifesto completo dos arquivos de mídia gerados para a tarefa,
    incluindo URLs de streaming nativo para player e links diretos de download.
    """
    task = await _get_user_task(task_id, current_user, db)
    manifest = scan_task_media_dir(task_id=task.id, business_id=task.business_id)

    # Enriquecimento com metadados adicionais do resultado registrado na tarefa
    if task.result and isinstance(task.result, dict):
        manifest["task_title"] = task.title
        manifest["task_status"] = task.status
        if "media" in task.result and isinstance(task.result["media"], dict):
            media_info = task.result["media"]
            if manifest.get("video") and "video" in media_info:
                manifest["video"]["duration_seconds"] = media_info["video"].get("duration_seconds", 60.0)
                manifest["video"]["resolution"] = media_info["video"].get("resolution", "1080x1920")
                manifest["video"]["aspect_ratio"] = media_info["video"].get("aspect_ratio", "9:16")
            if manifest.get("audio") and "audio" in media_info:
                manifest["audio"]["duration_seconds"] = media_info["audio"].get("duration_seconds")
                manifest["audio"]["provider"] = media_info["audio"].get("provider", "ElevenLabs / EdgeTTS")

    return {"data": manifest}


@router.patch("/{task_id}/move")
async def move(
    task_id: int,
    payload: TaskMoveRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)

    target_status = normalize_task_status(payload.status, task.assignee)
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

    # Dispara execução autônoma com IA Worker e Pipeline Multimídia se movido para in_progress_agent
    if target_status == "in_progress_agent" and task.assignee == "agent":
        background_tasks.add_task(_bg_execute_task, task.id, current_user)

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
        if field == "status" and val is not None:
            val = normalize_task_status(val, task.assignee)
        setattr(task, field, val)

    task.updated_at = _utc_now()
    await db.commit()
    await db.refresh(task)

    return {"data": _format_task(task)}


@router.post("/{task_id}/execute")
async def execute(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await execute_agent_task(db, task_id, current_user)
        return {"message": "Tarefa executada com sucesso pelo IA Worker!", **res}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao executar tarefa com IA: {str(e)}",
        )


@router.post("/execute-pending")
async def execute_pending(
    business_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task.id).where(
        Task.user_id == current_user.id,
        Task.assignee == "agent",
        Task.status.in_(["in_progress_agent", "backlog", "ready", "in_progress"]),
        Task.deleted_at.is_(None),
    )
    if business_id:
        query = query.where(Task.business_id == business_id)

    res = await db.execute(query.order_by(Task.id.asc()).limit(10))
    task_ids = res.scalars().all()

    executed = []
    errors = []
    for tid in task_ids:
        try:
            r = await execute_agent_task(db, tid, current_user)
            executed.append({"task_id": tid, "status": r["status"], "summary": r["summary"]})
        except Exception as e:
            errors.append({"task_id": tid, "error": str(e)})

    return {
        "message": f"{len(executed)} tarefas executadas com sucesso.",
        "executed": executed,
        "errors": errors,
    }


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)
    delete_task_storage_dirs(task_id=task.id, business_id=task.business_id)
    task.deleted_at = _utc_now()
    await db.commit()
    return None

