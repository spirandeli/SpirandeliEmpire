import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.database import get_db, AsyncSessionLocal
from src.dependencies import get_current_user
from src.models import ApprovalQueue, Business, ContentAsset, Task, User
from src.schemas.task import (
    TaskCreateRequest,
    TaskMoveRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from src.services.task_executor_service import execute_agent_task
from src.services.media.pipeline import _persist_video_progress
from src.routers.media import scan_task_media_dir
from src.routers.storage_viewer import delete_task_storage_dirs

logger = logging.getLogger("abvos.routers.tasks")

_RUNNING_TASK_IDS: set[int] = set()


async def _bg_execute_task(task_id: int, user: User | int):
    """
    Executa a tarefa em background de forma assíncrona sem bloquear a requisição HTTP.
    """
    if task_id in _RUNNING_TASK_IDS:
        logger.info(f"Tarefa #{task_id} já está em execução em segundo plano. Ignorando disparo duplicado.")
        return

    _RUNNING_TASK_IDS.add(task_id)
    user_id = user.id if hasattr(user, "id") else int(user)
    try:
        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).where(User.id == user_id))
            db_user = u_res.scalar_one_or_none()
            if db_user:
                await execute_agent_task(session, task_id, db_user)
    except Exception as e:
        logger.error(f"Erro ao executar tarefa #{task_id} em background: {e}")
    finally:
        _RUNNING_TASK_IDS.discard(task_id)

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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_user_task(task_id, current_user, db)
    now = _utc_now()
    task.status = "in_progress_agent"
    task.started_at = now
    task.failure_reason = None
    task.updated_at = now
    await db.commit()
    await db.refresh(task)

    await _persist_video_progress(
        task_id=task.id,
        business_id=task.business_id or 0,
        current_scene=0,
        total_scenes=20,
        stage="prompts",
        percent=0.0,
    )
    await db.refresh(task)

    # Dispara a execução pesada em background para responder imediatamente (< 50ms) sem deixar a requisição pendente
    background_tasks.add_task(_bg_execute_task, task.id, current_user.id)

    return {
        "message": "Execução iniciada em segundo plano pelo IA Worker! Acompanhe o progresso no card.",
        "task_id": task.id,
        "status": "in_progress_agent",
        "data": _format_task(task),
    }


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


class RunAgentStageRequest(BaseModel):
    cascade: bool = True
    feedback: Optional[str] = None
    sync: bool = False


class RegenerateSceneRequest(BaseModel):
    custom_prompt: Optional[str] = None
    reassemble: bool = False
    sync: bool = False


async def _resolve_parent_task(task: Task, user: User, db: AsyncSession) -> Task:
    if task.parent_id:
        p_res = await db.execute(
            select(Task).options(selectinload(Task.business)).where(
                Task.id == task.parent_id,
                Task.user_id == user.id,
                Task.deleted_at.is_(None),
            )
        )
        parent = p_res.scalar_one_or_none()
        if parent:
            return parent
    return task


async def _bg_run_stage(task_id: int, user_id: int, stage_val: str, cascade: bool, feedback: Optional[str]) -> None:
    from src.services.media.agents.contracts import AgentStage
    from src.services.media.agents.orchestrator import VideoOrchestrator

    async with AsyncSessionLocal() as session:
        u_res = await session.execute(select(User).where(User.id == user_id))
        db_user = u_res.scalar_one_or_none()
        t_res = await session.execute(select(Task).options(selectinload(Task.business)).where(Task.id == task_id))
        db_task = t_res.scalar_one_or_none()
        if db_user and db_task:
            await VideoOrchestrator().run_single_stage(
                db=session,
                parent_task=db_task,
                user=db_user,
                stage=AgentStage(stage_val),
                cascade=cascade,
                feedback=feedback,
            )


async def _bg_continue_pipeline(task_id: int, user_id: int) -> None:
    from src.services.media.agents.orchestrator import VideoOrchestrator

    async with AsyncSessionLocal() as session:
        u_res = await session.execute(select(User).where(User.id == user_id))
        db_user = u_res.scalar_one_or_none()
        t_res = await session.execute(select(Task).options(selectinload(Task.business)).where(Task.id == task_id))
        db_task = t_res.scalar_one_or_none()
        if db_user and db_task:
            await VideoOrchestrator().run_pipeline(
                db=session,
                parent_task=db_task,
                user=db_user,
                pause_after_script=False,
            )


async def _bg_regenerate_scene(
    task_id: int,
    user_id: int,
    scene_number: int,
    custom_prompt: Optional[str],
    reassemble: bool,
) -> None:
    from src.services.media.agents.orchestrator import VideoOrchestrator

    async with AsyncSessionLocal() as session:
        u_res = await session.execute(select(User).where(User.id == user_id))
        db_user = u_res.scalar_one_or_none()
        t_res = await session.execute(select(Task).options(selectinload(Task.business)).where(Task.id == task_id))
        db_task = t_res.scalar_one_or_none()
        if db_user and db_task:
            await VideoOrchestrator().regenerate_scene(
                db=session,
                parent_task=db_task,
                user=db_user,
                scene_number=scene_number,
                custom_prompt=custom_prompt,
                reassemble=reassemble,
            )


@router.get("/{task_id}/pipeline")
async def get_task_pipeline(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o manifesto completo dos 5 agentes e suas subtarefas agrupadas."""
    from src.services.media.agents.base import load_manifest
    from src.services.media.agents.contracts import STAGE_METADATA, STAGE_ORDER
    from src.services.media.agents.orchestrator import VideoOrchestrator

    task = await _get_user_task(task_id, current_user, db)
    parent = await _resolve_parent_task(task, current_user, db)

    orchestrator = VideoOrchestrator()
    ctx = await orchestrator.build_context(db, parent, current_user)
    manifest = load_manifest(ctx)

    sub_res = await db.execute(
        select(Task)
        .options(selectinload(Task.business))
        .where(Task.parent_id == parent.id, Task.deleted_at.is_(None))
        .order_by(Task.position.asc(), Task.id.asc())
    )
    subtasks = sub_res.scalars().all()
    sub_by_stage = {
        (st.payload or {}).get("pipeline_stage"): _format_task(st)
        for st in subtasks
        if (st.payload or {}).get("pipeline_stage")
    }

    stages_view = []
    for st in STAGE_ORDER:
        meta = STAGE_METADATA[st.value]
        stages_view.append({
            "stage": st.value,
            "order": meta["order"],
            "agent_action": meta["agent_action"],
            "label": meta["label"],
            "short_label": meta["short_label"],
            "description": meta["description"],
            "manifest_status": manifest.stage_statuses.get(st.value, "pending"),
            "subtask": sub_by_stage.get(st.value),
        })

    return {
        "data": {
            "parent_task": _format_task(parent),
            "script_approved": bool((parent.payload or {}).get("script_approved", False)),
            "manifest": manifest.model_dump(mode="json"),
            "stages": stages_view,
        }
    }


@router.post("/{task_id}/agents/continue")
async def continue_video_pipeline(
    task_id: int,
    background_tasks: BackgroundTasks,
    sync: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aprova o roteiro (Agente 1) e libera a execução encadeada dos Agentes 2 a 5."""
    from src.services.media.agents.orchestrator import VideoOrchestrator

    task = await _get_user_task(task_id, current_user, db)
    parent = await _resolve_parent_task(task, current_user, db)
    now = _utc_now()

    payload = dict(parent.payload or {})
    payload["script_approved"] = True
    payload["pause_after_script"] = False
    parent.payload = payload
    parent.status = "in_progress_agent"
    parent.status_log = "Roteiro aprovado! Iniciando Agentes 2 a 5..."
    parent.updated_at = now

    # Atualiza aprovações pendentes e ContentAsset associados
    ap_res = await db.execute(
        select(ApprovalQueue).where(
            ApprovalQueue.task_id == parent.id,
            ApprovalQueue.status == "pending",
        )
    )
    for appr in ap_res.scalars().all():
        appr.status = "approved"
        appr.reviewed_at = now
        appr.updated_at = now

    if payload.get("content_asset_id"):
        ca_res = await db.execute(select(ContentAsset).where(ContentAsset.id == int(payload["content_asset_id"])))
        ca = ca_res.scalar_one_or_none()
        if ca:
            ca.status = "approved"
            ca.updated_at = now

    await db.commit()
    await db.refresh(parent)

    if sync:
        res = await VideoOrchestrator().run_pipeline(
            db=db,
            parent_task=parent,
            user=current_user,
            pause_after_script=False,
        )
        return {"message": "Pipeline concluído!", "data": res}

    background_tasks.add_task(_bg_continue_pipeline, parent.id, current_user.id)
    return {
        "message": "Roteiro aprovado! Agentes 2 (Cenas Gemini), 3 (Narração), 4 (Legendas) e 5 (Montagem) iniciados.",
        "task_id": parent.id,
        "status": "in_progress_agent",
        "data": _format_task(parent),
    }


@router.post("/{task_id}/agents/{stage}/run")
async def run_agent_stage(
    task_id: int,
    stage: str,
    body: RunAgentStageRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executa ou re-executa um dos 5 agentes isoladamente (com opção de cascata)."""
    from src.services.media.agents.contracts import AgentStage
    from src.services.media.agents.orchestrator import VideoOrchestrator

    try:
        target_stage = AgentStage(stage)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Estágio inválido '{stage}'. Use: script, video_scenes, narration, subtitles ou assemble.",
        )

    task = await _get_user_task(task_id, current_user, db)
    parent = await _resolve_parent_task(task, current_user, db)

    if body.sync:
        res = await VideoOrchestrator().run_single_stage(
            db=db,
            parent_task=parent,
            user=current_user,
            stage=target_stage,
            cascade=body.cascade,
            feedback=body.feedback,
        )
        return {"message": f"Agente '{target_stage.value}' executado!", "data": res}

    parent.status = "in_progress_agent"
    parent.status_log = f"Executando agente '{target_stage.value}'..."
    parent.updated_at = _utc_now()
    await db.commit()
    background_tasks.add_task(_bg_run_stage, parent.id, current_user.id, target_stage.value, body.cascade, body.feedback)
    return {
        "message": f"Agente '{target_stage.value}' disparado em segundo plano.",
        "task_id": parent.id,
        "stage": target_stage.value,
    }


@router.post("/{task_id}/scenes/{scene_number}/regenerate")
async def regenerate_task_scene(
    task_id: int,
    scene_number: int,
    body: RegenerateSceneRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenera apenas uma cena específica via Agente 2 (Gemini Image)."""
    from src.services.media.agents.orchestrator import VideoOrchestrator

    if scene_number < 1 or scene_number > 40:
        raise HTTPException(status_code=400, detail="Número de cena inválido.")

    task = await _get_user_task(task_id, current_user, db)
    parent = await _resolve_parent_task(task, current_user, db)

    if body.sync:
        res = await VideoOrchestrator().regenerate_scene(
            db=db,
            parent_task=parent,
            user=current_user,
            scene_number=scene_number,
            custom_prompt=body.custom_prompt,
            reassemble=body.reassemble,
        )
        return {"message": f"Cena #{scene_number} regenerada com Gemini!", "data": res}

    background_tasks.add_task(
        _bg_regenerate_scene,
        parent.id,
        current_user.id,
        scene_number,
        body.custom_prompt,
        body.reassemble,
    )
    return {
        "message": f"Regeneração da Cena #{scene_number} iniciada via Gemini.",
        "task_id": parent.id,
        "scene_number": scene_number,
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

