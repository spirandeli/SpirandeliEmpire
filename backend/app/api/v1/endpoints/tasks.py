"""SpirandeliEmpire OS 3.1 — Tasks API Endpoints"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.task_service import task_service

router = APIRouter()


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    assigned_agent_id: str = "jeffrey"
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|in_progress|completed|failed|blocked|waiting_approval)$")
    result_summary: Optional[str] = None


@router.get("/")
async def list_tasks(
    project_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    return await task_service.list_tasks(
        project_id=project_id,
        agent_id=agent_id,
        workflow_id=workflow_id,
        status=status_filter,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreateRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    return await task_service.create_task(
        title=body.title,
        description=body.description,
        assigned_agent_id=body.assigned_agent_id,
        project_id=body.project_id,
        workflow_id=body.workflow_id,
        priority=body.priority,
        user_id=current_user.id,
    )


@router.get("/{task_id}")
async def get_task(task_id: str, current_user: UserModel = Depends(get_current_user)):
    task = await task_service.get_task(task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    updated = await task_service.update_task_status(task_id, body.status, body.result_summary, user_id=current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": body.status}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    deleted = await task_service.delete_task(task_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
