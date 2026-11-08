from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.dependencies import require_admin
from src.models import AiUsageLog, User

router = APIRouter(prefix="/admin/ai-governance", tags=["Admin AI Governance"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UpdateLimitsRequest(BaseModel):
    monthly_token_limit: int = Field(..., ge=10000, le=500000000)
    is_ai_active: Optional[bool] = None


@router.get("/stats")
async def stats(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = _utc_now()
    start_of_month = datetime(now.year, now.month, 1)

    # 1. Métricas Globais
    tokens_res = await db.execute(
        select(func.sum(AiUsageLog.total_tokens)).where(AiUsageLog.created_at >= start_of_month)
    )
    monthly_tokens = tokens_res.scalar() or 0

    cost_res = await db.execute(
        select(func.sum(AiUsageLog.estimated_cost_usd)).where(AiUsageLog.created_at >= start_of_month)
    )
    monthly_cost_usd = float(cost_res.scalar() or 0.0)
    monthly_cost_brl = round(monthly_cost_usd * 5.80, 2)

    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    active_ai_res = await db.execute(select(func.count(User.id)).where(User.is_ai_active == True))
    active_ai_users = active_ai_res.scalar() or 0
    blocked_users = total_users - active_ai_users

    # 2. Ranking de Usuários
    users_res = await db.execute(
        select(User)
        .options(selectinload(User.businesses), selectinload(User.tasks))
        .order_by(User.tokens_used_this_month.desc())
    )
    users = users_res.scalars().all()

    users_data = []
    for u in users:
        limit = u.monthly_token_limit or 1
        pct = round((u.tokens_used_this_month / limit) * 100, 1)
        users_data.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_ai_active": u.is_ai_active,
            "monthly_token_limit": u.monthly_token_limit,
            "tokens_used_this_month": u.tokens_used_this_month,
            "usage_percentage": min(100.0, pct),
            "is_exceeded": u.tokens_used_this_month >= limit,
            "cost_usd": 0.0,
            "cost_brl": 0.0,
            "businesses_count": len(u.businesses),
            "tasks_count": len(u.tasks),
        })

    # 3. Logs recentes
    logs_res = await db.execute(
        select(AiUsageLog).order_by(AiUsageLog.id.desc()).limit(25)
    )
    recent_logs = [
        {
            "id": l.id,
            "model": l.model,
            "context": l.context,
            "prompt_tokens": l.prompt_tokens,
            "completion_tokens": l.completion_tokens,
            "total_tokens": l.total_tokens,
            "estimated_cost_usd": float(l.estimated_cost_usd),
            "latency_ms": l.latency_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs_res.scalars().all()
    ]

    return {
        "metrics": {
            "monthly_tokens": monthly_tokens,
            "monthly_cost_usd": round(monthly_cost_usd, 4),
            "monthly_cost_brl": monthly_cost_brl,
            "total_users": total_users,
            "active_ai_users": active_ai_users,
            "blocked_users": blocked_users,
        },
        "users": users_data,
        "by_model": [],
        "by_context": [],
        "recent_logs": recent_logs,
    }


@router.patch("/users/{user_id}/limits")
async def update_limits(
    user_id: int,
    payload: UpdateLimitsRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    u.monthly_token_limit = payload.monthly_token_limit
    if payload.is_ai_active is not None:
        u.is_ai_active = payload.is_ai_active

    await db.commit()
    return {
        "message": f"Limites do usuário {u.name} atualizados com sucesso.",
        "user": {
            "id": u.id,
            "monthly_token_limit": u.monthly_token_limit,
            "is_ai_active": u.is_ai_active,
        },
    }


@router.post("/users/{user_id}/kill-switch")
async def toggle_kill_switch(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    new_state = not u.is_ai_active
    u.is_ai_active = new_state
    await db.commit()

    return {
        "message": f"Acesso à IA {'ATIVADO' if new_state else 'BLOQUEADO'} para {u.name}.",
        "is_ai_active": new_state,
    }


@router.post("/users/{user_id}/reset-usage")
async def reset_usage(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    u.tokens_used_this_month = 0
    await db.commit()

    return {
        "message": f"Consumo mensal de tokens de {u.name} foi resetado para zero.",
        "tokens_used_this_month": 0,
    }


@router.post("/knowledge/reindex")
async def reindex_knowledge_endpoint(
    force: bool = True,
    current_admin: User = Depends(require_admin),
):
    from src.services.knowledge_service import index_all_knowledge
    result = await index_all_knowledge(force=force)
    return {
        "message": "Base de conhecimento re-indexada com sucesso.",
        "data": result,
    }


@router.get("/knowledge/stats")
async def knowledge_stats_endpoint(
    current_admin: User = Depends(require_admin),
):
    from src.services.knowledge_service import get_knowledge_stats
    return {"data": get_knowledge_stats()}


