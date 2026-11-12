"""SpirandeliEmpire OS 3.1 — Projects API Endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.project_service import project_service

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1)
    project_type: str = "software"
    priority: str = "medium"
    department: str = "development"
    objectives: Optional[List[str]] = None
    lead_agent_id: str = "jeffrey"
    auto_start_workflow: bool = True


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|completed|paused|archived)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high|urgent)$")


class DigitalBusinessWizardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    niche: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    monetization: str
    budget: str = "Bootstrapped"


@router.get("/")
async def list_projects(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    project_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    return await project_service.list_projects(
        status=status_filter,
        project_type=project_type,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    return await project_service.create_project(
        name=body.name,
        description=body.description,
        project_type=body.project_type,
        priority=body.priority,
        department=body.department,
        objectives=body.objectives,
        lead_agent_id=body.lead_agent_id,
        auto_start_workflow=body.auto_start_workflow,
        user_id=current_user.id,
    )


@router.post("/digital-business", status_code=status.HTTP_201_CREATED)
async def create_digital_business(
    body: DigitalBusinessWizardRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    return await project_service.create_digital_business(body.model_dump(), user_id=current_user.id)


@router.get("/{project_id}")
async def get_project(project_id: str, current_user: UserModel = Depends(get_current_user)):
    res = await project_service.get_project_details(project_id, user_id=current_user.id)
    if not res:
        raise HTTPException(status_code=404, detail="Project not found")
    return res


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    res = await project_service.update_project(project_id, body.model_dump(exclude_unset=True), user_id=current_user.id)
    if not res:
        raise HTTPException(status_code=404, detail="Project not found")
    return res


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    deleted = await project_service.delete_project(project_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
