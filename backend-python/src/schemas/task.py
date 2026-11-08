from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class TaskCreateRequest(BaseModel):
    business_id: int
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    assignee: str = "user" # agent ou user
    status: Optional[str] = None # se omitido: backlog ou todo_user
    priority: str = "medium" # low, medium, high, urgent
    due_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None


class TaskMoveRequest(BaseModel):
    status: str
    position: Optional[int] = 0


class TaskResponse(BaseModel):
    id: int
    business_id: int
    business: Optional[dict[str, Any]] = None
    parent_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    assignee: str
    assignee_label: str
    status: str
    status_label: str
    priority: str
    source: str
    position: int
    due_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_action: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    failure_reason: Optional[str] = None
    status_log: Optional[str] = None
    attempts: int = 0
    external_calendar_provider: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

