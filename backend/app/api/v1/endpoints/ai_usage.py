"""SpirandeliEmpire OS 3.2 — AI Usage & Consumption Monitoring Endpoints"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from app.auth.dependencies import get_current_user
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, AIUsageRecordModel

router = APIRouter()


@router.get("/")
async def get_usage_summary(
    limit: int = Query(50, ge=1, le=200),
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        totals_res = await session.execute(
            select(
                func.count(AIUsageRecordModel.id),
                func.coalesce(func.sum(AIUsageRecordModel.input_tokens), 0),
                func.coalesce(func.sum(AIUsageRecordModel.output_tokens), 0),
                func.coalesce(func.sum(AIUsageRecordModel.total_tokens), 0),
            ).where(AIUsageRecordModel.user_id == current_user.id)
        )
        req_count, in_tok, out_tok, tot_tok = totals_res.one()

        rec_res = await session.execute(
            select(AIUsageRecordModel)
            .where(AIUsageRecordModel.user_id == current_user.id)
            .order_by(AIUsageRecordModel.created_at.desc())
            .limit(limit)
        )
        records = [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "provider": r.provider,
                "model_id": r.model_id,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "duration_ms": r.duration_ms,
                "status": r.status,
                "fallback_from": r.fallback_from,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rec_res.scalars().all()
        ]
    return {
        "totals": {
            "requests": int(req_count or 0),
            "input_tokens": int(in_tok or 0),
            "output_tokens": int(out_tok or 0),
            "total_tokens": int(tot_tok or 0),
        },
        "records": records,
    }


@router.get("/agents")
async def get_usage_by_agent(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                AIUsageRecordModel.agent_id,
                func.count(AIUsageRecordModel.id),
                func.coalesce(func.sum(AIUsageRecordModel.total_tokens), 0),
            )
            .where(AIUsageRecordModel.user_id == current_user.id)
            .group_by(AIUsageRecordModel.agent_id)
        )
        return [
            {"agent_id": row[0] or "system", "requests": int(row[1]), "total_tokens": int(row[2])}
            for row in res.all()
        ]


@router.get("/models")
async def get_usage_by_model(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                AIUsageRecordModel.provider,
                AIUsageRecordModel.model_id,
                func.count(AIUsageRecordModel.id),
                func.coalesce(func.sum(AIUsageRecordModel.total_tokens), 0),
            )
            .where(AIUsageRecordModel.user_id == current_user.id)
            .group_by(AIUsageRecordModel.provider, AIUsageRecordModel.model_id)
        )
        return [
            {"provider": row[0], "model_id": row[1], "requests": int(row[2]), "total_tokens": int(row[3])}
            for row in res.all()
        ]


@router.get("/providers")
async def get_usage_by_provider(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                AIUsageRecordModel.provider,
                func.count(AIUsageRecordModel.id),
                func.coalesce(func.sum(AIUsageRecordModel.total_tokens), 0),
            )
            .where(AIUsageRecordModel.user_id == current_user.id)
            .group_by(AIUsageRecordModel.provider)
        )
        return [
            {"provider": row[0], "requests": int(row[1]), "total_tokens": int(row[2])}
            for row in res.all()
        ]

