"""SpirandeliEmpire OS 3.1 — Approvals API Endpoints"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.approval_service import approval_service

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


@router.get("/")
async def list_approvals(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    items = await approval_service.list_approvals(status=status, user_id=current_user.id)
    return items[offset : offset + limit]


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    try:
        return await approval_service.decide_approval(
            approval_id=approval_id,
            approved=body.approved,
            feedback=body.feedback,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
