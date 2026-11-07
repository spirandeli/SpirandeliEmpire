from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class ApproveRequest(BaseModel):
    scheduled_for: Optional[datetime] = None
    selected_hook_index: Optional[int] = None


class RevisionRequest(BaseModel):
    feedback: str = Field(..., min_length=3)
    section: Optional[str] = "all" # hooks, script, caption, visual_prompts, all


class RejectRequest(BaseModel):
    reason: Optional[str] = "Descartado pelo operador"
    discard_product: bool = False


class ApprovalQueueResponse(BaseModel):
    id: int
    business_id: int
    business: Optional[dict[str, Any]] = None
    task_id: Optional[int] = None
    type: str
    title: str
    summary: Optional[str] = None
    payload: dict[str, Any]
    status: str
    priority: str
    agent_confidence: Optional[Decimal] = None
    reviewer_feedback: Optional[str] = None
    revision_count: int = 0
    revision_history: Optional[list[dict[str, Any]]] = None
    reviewed_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
