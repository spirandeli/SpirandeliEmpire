from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from src.database import get_db
from src.dependencies import get_current_user
from src.models import ApprovalQueue, Task, User
from src.schemas.approval import (
    ApprovalQueueResponse,
    ApproveRequest,
    RejectRequest,
    RevisionRequest,
)

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _format_approval(appr: ApprovalQueue) -> dict[str, Any]:
    biz_data = None
    if appr.business:
        biz_data = {"id": appr.business.id, "name": appr.business.name}

    return {
        "id": appr.id,
        "business_id": appr.business_id,
        "business": biz_data,
        "task_id": appr.task_id,
        "type": appr.type,
        "title": appr.title,
        "summary": appr.summary,
        "payload": appr.payload,
        "status": appr.status,
        "priority": appr.priority,
        "agent_confidence": float(appr.agent_confidence) if appr.agent_confidence else None,
        "reviewer_feedback": appr.reviewer_feedback,
        "revision_count": appr.revision_count,
        "revision_history": appr.revision_history,
        "reviewed_at": appr.reviewed_at.isoformat() if appr.reviewed_at else None,
        "scheduled_for": appr.scheduled_for.isoformat() if appr.scheduled_for else None,
        "expires_at": appr.expires_at.isoformat() if appr.expires_at else None,
        "created_at": appr.created_at.isoformat() if appr.created_at else None,
        "updated_at": appr.updated_at.isoformat() if appr.updated_at else None,
    }


async def _get_user_approval(approval_id: int, user: User, db: AsyncSession) -> ApprovalQueue:
    res = await db.execute(
        select(ApprovalQueue)
        .options(selectinload(ApprovalQueue.business), selectinload(ApprovalQueue.task))
        .where(ApprovalQueue.id == approval_id, ApprovalQueue.user_id == user.id)
    )
    appr = res.scalar_one_or_none()
    if not appr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item de aprovação não encontrado ou sem permissão de acesso.",
        )
    return appr


@router.get("/summary")
async def summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pending = (
        await db.execute(
            select(func.count(ApprovalQueue.id)).where(
                ApprovalQueue.user_id == current_user.id,
                ApprovalQueue.status == "pending",
            )
        )
    ).scalar() or 0

    revision = (
        await db.execute(
            select(func.count(ApprovalQueue.id)).where(
                ApprovalQueue.user_id == current_user.id,
                ApprovalQueue.status == "revision_requested",
            )
        )
    ).scalar() or 0

    return {
        "data": {
            "pending": pending,
            "revision": revision,
            "total_awaiting": pending + revision,
        }
    }


@router.get("")
async def index(
    status_filter: Optional[str] = Query("awaiting", alias="status"),
    business_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ApprovalQueue)
        .options(selectinload(ApprovalQueue.business))
        .where(ApprovalQueue.user_id == current_user.id)
    )

    if status_filter == "awaiting":
        query = query.where(ApprovalQueue.status.in_(["pending", "revision_requested"]))
    elif status_filter:
        query = query.where(ApprovalQueue.status == status_filter)

    if business_id:
        query = query.where(ApprovalQueue.business_id == business_id)

    query = query.order_by(ApprovalQueue.id.desc())
    res = await db.execute(query)
    items = res.scalars().all()

    return {"data": [_format_approval(item) for item in items]}


@router.get("/{approval_id}")
async def show(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appr = await _get_user_approval(approval_id, current_user, db)
    return {"data": _format_approval(appr)}


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: int,
    payload: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appr = await _get_user_approval(approval_id, current_user, db)

    now = _utc_now()
    appr.status = "scheduled" if payload.scheduled_for else "approved"
    appr.scheduled_for = payload.scheduled_for
    appr.reviewed_at = now

    item_payload = dict(appr.payload or {})
    if payload.selected_hook_index is not None:
        item_payload["selected_hook_index"] = payload.selected_hook_index
    appr.payload = item_payload

    # Atualiza a tarefa associada para done
    if appr.task:
        appr.task.status = "done"
        appr.task.completed_at = now

    appr.updated_at = now
    await db.commit()
    await db.refresh(appr)

    return {"data": _format_approval(appr)}


@router.post("/{approval_id}/revision")
async def revision(
    approval_id: int,
    payload: RevisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appr = await _get_user_approval(approval_id, current_user, db)

    now = _utc_now()
    appr.status = "revision_requested"
    appr.reviewer_feedback = payload.feedback
    appr.revision_count = (appr.revision_count or 0) + 1

    history = list(appr.revision_history or [])
    history.append({
        "revision": appr.revision_count,
        "requested_at": now.isoformat(),
        "feedback": payload.feedback,
        "section": payload.section,
    })
    appr.revision_history = history

    # Tarefa volta para o agente
    if appr.task:
        appr.task.status = "in_progress_agent"

    appr.updated_at = now
    await db.commit()
    await db.refresh(appr)

    return {"data": _format_approval(appr)}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: int,
    payload: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appr = await _get_user_approval(approval_id, current_user, db)

    now = _utc_now()
    appr.status = "rejected"
    appr.reviewer_feedback = payload.reason
    appr.reviewed_at = now

    if appr.task:
        appr.task.status = "done"
        appr.task.completed_at = now

    appr.updated_at = now
    await db.commit()
    await db.refresh(appr)

    return {"data": _format_approval(appr)}

