"""SpirandeliEmpire OS 3.1 — Workflows API Endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.auth.dependencies import get_current_user, require_role
from app.database.session import AsyncSessionLocal
from app.database.models import WorkflowModel, UserModel
from app.orchestrator.workflows.manager import workflow_manager
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager

router = APIRouter()


class StartWorkflowRequest(BaseModel):
    user_request: str = Field(..., min_length=1, max_length=4000)
    workflow_type: str = Field(default="supervisor", pattern="^(supervisor|development|content|clip|business)$")
    project_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ResumeWorkflowRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


@router.get("/")
async def list_workflows(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    workflow_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        query = select(WorkflowModel).where(WorkflowModel.user_id == current_user.id)
        if status_filter:
            query = query.where(WorkflowModel.status == status_filter)
        if workflow_type:
            query = query.where(WorkflowModel.workflow_type == workflow_type)
        result = await session.execute(
            query.order_by(WorkflowModel.created_at.desc()).offset(offset).limit(limit)
        )
        wfs = result.scalars().all()
        return [
            {
                "id": w.id,
                "project_id": w.project_id,
                "title": w.title,
                "workflow_type": w.workflow_type,
                "status": w.status,
                "current_node": w.current_node,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in wfs
        ]


@router.post("/start")
async def start_workflow(
    body: StartWorkflowRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    return await workflow_manager.start_workflow(
        user_request=body.user_request,
        workflow_type=body.workflow_type,
        project_id=body.project_id,
        context=body.context,
        user_id=current_user.id,
    )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        wf = await session.get(WorkflowModel, workflow_id)
        if not wf or wf.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {
            "id": wf.id,
            "project_id": wf.project_id,
            "title": wf.title,
            "workflow_type": wf.workflow_type,
            "status": wf.status,
            "current_node": wf.current_node,
            "graph_state": wf.graph_state,
            "quality_results": wf.quality_results or [],
            "errors": wf.errors or [],
            "checkpoints": checkpoint_manager.get_checkpoints(workflow_id),
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
        }


@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    body: ResumeWorkflowRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    async with AsyncSessionLocal() as session:
        wf = await session.get(WorkflowModel, workflow_id)
        if not wf or wf.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        return await workflow_manager.resume_workflow(
            workflow_id=workflow_id,
            approved=body.approved,
            feedback=body.feedback,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    async with AsyncSessionLocal() as session:
        wf = await session.get(WorkflowModel, workflow_id)
        if not wf or wf.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        return await workflow_manager.cancel_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{workflow_id}/checkpoints")
async def get_workflow_checkpoints(
    workflow_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        wf = await session.get(WorkflowModel, workflow_id)
        if not wf or wf.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Workflow not found")
    return checkpoint_manager.get_checkpoints(workflow_id)
